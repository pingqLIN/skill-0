from __future__ import annotations

import json

from fastapi.testclient import TestClient

import api.main as api_module
from asset_registry.search import AssetSearchResult


def _write_skill(path, *, name="asset-api", skill_id="claude__skill__asset_api"):
    path.write_text(
        json.dumps(
            {
                "meta": {
                    "skill_id": skill_id,
                    "name": name,
                    "description": "Asset API fixture",
                    "parsed_by": "asset-api-test",
                    "parser_version": "1.0.0",
                },
                "decomposition": {"actions": [], "rules": [], "directives": []},
            }
        ),
        encoding="utf-8",
    )


def test_asset_list_detail_and_revisions_are_read_only_projections(
    tmp_path, monkeypatch
):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    _write_skill(parsed / "asset.json")
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed))
    client = TestClient(api_module.app)

    listed = client.get("/api/assets")
    assert listed.status_code == 200
    assert listed.json() == [
        {
            "asset_id": "claude__skill__asset_api",
            "asset_type": "skill",
            "name": "asset-api",
            "summary": "Asset API fixture",
            "revision_count": 1,
            "ambiguous": False,
        }
    ]

    detail = client.get("/api/assets/claude__skill__asset_api")
    assert detail.status_code == 200
    assert detail.json()["payload"] is None
    with_payload = client.get(
        "/api/assets/claude__skill__asset_api", params={"include_payload": True}
    )
    assert with_payload.status_code == 200
    assert with_payload.json()["payload"]["meta"]["skill_id"] == "claude__skill__asset_api"

    revisions = client.get("/api/assets/claude__skill__asset_api/revisions")
    assert revisions.status_code == 200
    assert len(revisions.json()) == 1
    assert revisions.json()[0]["payload"] is None


def test_ambiguous_asset_lists_revisions_but_detail_fails_closed(tmp_path, monkeypatch):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    _write_skill(parsed / "one.json", name="one")
    _write_skill(parsed / "two.json", name="two")
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed))
    client = TestClient(api_module.app)

    listed = client.get("/api/assets").json()
    assert listed[0]["ambiguous"] is True
    assert listed[0]["revision_count"] == 2
    assert len(
        client.get("/api/assets/claude__skill__asset_api/revisions").json()
    ) == 2
    detail = client.get("/api/assets/claude__skill__asset_api")
    assert detail.status_code == 409
    assert detail.json()["detail"]["code"] == "ambiguous_asset_identity"


def test_asset_search_uses_generic_projection(monkeypatch):
    class FakeSearchEngine:
        def search_assets(self, query, *, asset_types, limit):
            assert query == "doctor"
            assert asset_types == ("skill",)
            assert limit == 3
            return [
                AssetSearchResult(
                    asset_id="claude__skill__doctor",
                    revision_id="asset-revision:sha256:" + "a" * 64,
                    asset_type="skill",
                    name="doctor",
                    description="fixture",
                    source_path="doctor.json",
                    distance=0.25,
                    similarity=0.8,
                )
            ]

    monkeypatch.setattr(api_module, "search_engine", FakeSearchEngine())
    response = TestClient(api_module.app).post(
        "/api/assets/search",
        json={"query": "doctor", "asset_types": ["skill"], "limit": 3},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["asset_id"] == "claude__skill__doctor"
    assert "payload" not in response.json()["results"][0]


def test_checked_in_legacy_alias_lists_canonical_revisions(root, monkeypatch):
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(root / "parsed"))
    client = TestClient(api_module.app)
    response = client.get(
        "/api/assets/claude__skill__java_to_java_upgrade/revisions"
    )
    assert response.status_code == 200
    assert {item["asset_id"] for item in response.json()} == {
        "claude__skill__java_11_to_java_17_upgrade",
        "claude__skill__java_17_to_java_21_upgrade",
        "claude__skill__java_21_to_java_25_upgrade",
    }
    assert (
        client.get("/api/assets/claude__skill__java_to_java_upgrade").status_code
        == 409
    )


def test_authenticated_reload_recovers_stale_snapshot_atomically(tmp_path, monkeypatch):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    source = parsed / "asset.json"
    _write_skill(source)
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed))
    client = TestClient(api_module.app)
    assert client.get("/api/assets/claude__skill__asset_api").status_code == 200

    _write_skill(source, name="asset-api-reloaded")
    stale = client.get("/api/assets/claude__skill__asset_api")
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_source_snapshot"

    unauthenticated = client.post("/api/assets/reload")
    assert unauthenticated.status_code == 401
    token = api_module.create_access_token({"sub": "testadmin"})
    reloaded = client.post(
        "/api/assets/reload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reloaded.status_code == 200
    assert reloaded.json()["revision_count"] == 1
    fresh = client.get(
        "/api/assets/claude__skill__asset_api", params={"include_payload": True}
    )
    assert fresh.status_code == 200
    assert fresh.json()["payload"]["meta"]["name"] == "asset-api-reloaded"
