from __future__ import annotations

import base64
import binascii
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any, Callable, Iterator

from ..certification import (
    ReconciliationResult,
    ReconciliationStatus,
    file_digest,
    load_certification_manifest,
)
from ..digest import canonical_digest
from ..models import ActionResult, AdapterCallRejected


DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "adapters"
    / "local-pdf-filesystem"
    / "adapter-certification.json"
)
SUPPORTED_ACTION_ID = "a_006"
MAX_PDF_BYTES = 10 * 1024 * 1024
SAFE_PDF_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.pdf$", re.IGNORECASE)
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class LocalPdfAdapterError(RuntimeError):
    pass


class InvalidAdapterInput(AdapterCallRejected):
    error_code = "INVALID_ADAPTER_INPUT"


class IdempotencyConflict(AdapterCallRejected):
    error_code = "IDEMPOTENCY_CONFLICT"


class AdapterOutcomeUnknown(LocalPdfAdapterError):
    pass


class AdapterRateLimitExceeded(AdapterCallRejected):
    error_code = "RATE_LIMITED"

    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = max(0.0, retry_after_seconds)
        super().__init__(
            f"adapter rate limit exceeded; retry after {self.retry_after_seconds:.3f} seconds",
            evidence={"retry_after_seconds": self.retry_after_seconds},
        )


class LocalPdfFilesystemAdapter:
    """Bounded local PDF writer used as the first certification candidate.

    The adapter never reads credentials, never accesses the network, refuses
    overwrite or traversal, and stores only hashes of idempotency keys.
    """

    supports_dry_run = True
    adapter_id = "skill0.local-pdf-filesystem"
    adapter_version = "1.0.0"
    adapter_kind = "python"
    adapter_target = "runtime.adapters.local_pdf:LocalPdfFilesystemAdapter"

    def __init__(
        self,
        output_root: str | Path,
        state_db: str | Path,
        *,
        manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
        clock: Callable[[], float] | None = None,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        raw_output_root = Path(output_root)
        if raw_output_root.is_symlink():
            raise LocalPdfAdapterError("output root must not be a symlink")
        self.output_root = raw_output_root.resolve()
        if not self.output_root.is_dir():
            raise LocalPdfAdapterError(
                "output root must be a pre-existing, non-symlink directory"
            )
        raw_state_db = Path(state_db)
        if raw_state_db.parent.is_symlink():
            raise LocalPdfAdapterError("state DB parent must not be a symlink")
        self.state_db = raw_state_db.resolve()
        if not self.state_db.parent.is_dir():
            raise LocalPdfAdapterError(
                "state DB parent must be a pre-existing, non-symlink directory"
            )

        self.manifest = load_certification_manifest(manifest_path)
        adapter_manifest = self.manifest["adapter"]
        expected = {
            "id": self.adapter_id,
            "version": self.adapter_version,
            "kind": self.adapter_kind,
            "target": self.adapter_target,
        }
        if any(adapter_manifest[name] != value for name, value in expected.items()):
            raise LocalPdfAdapterError("adapter implementation identity does not match manifest")
        self.adapter_artifact_digest = file_digest(__file__)
        self.certification_manifest_digest = canonical_digest(self.manifest)
        self.max_requests = int(self.manifest["rate_limit"]["max_requests"])
        self.window_seconds = int(self.manifest["rate_limit"]["window_seconds"])
        self.max_concurrency = int(self.manifest["rate_limit"]["max_concurrency"])
        self.clock = clock or time.time
        self.fault_injector = fault_injector
        self._lock = threading.RLock()
        self._concurrency = threading.BoundedSemaphore(self.max_concurrency)
        self.connection = sqlite3.connect(
            self.state_db,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> LocalPdfFilesystemAdapter:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _initialize_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS adapter_operations (
                idempotency_key_digest TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                request_digest TEXT NOT NULL,
                resource_id TEXT NOT NULL UNIQUE,
                relative_path TEXT NOT NULL,
                content_digest TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('prepared', 'applied', 'compensated')),
                prepared_at TEXT NOT NULL,
                applied_at TEXT,
                compensation_evidence_json TEXT
            );
            CREATE TABLE IF NOT EXISTS adapter_compensations (
                compensation_key_digest TEXT PRIMARY KEY,
                resource_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('prepared', 'succeeded')),
                evidence_json TEXT,
                prepared_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS adapter_rate_windows (
                bucket TEXT PRIMARY KEY,
                window_start REAL NOT NULL,
                request_count INTEGER NOT NULL
            );
            """
        )

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        else:
            self.connection.execute("COMMIT")

    @staticmethod
    def _key_digest(value: str) -> str:
        if not isinstance(value, str) or not value or len(value) > 1024:
            raise InvalidAdapterInput("idempotency key is required")
        return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _prepare_request(
        self, action_id: str, parameters: dict[str, Any]
    ) -> tuple[str, bytes, str, str, str]:
        if action_id != SUPPORTED_ACTION_ID:
            raise InvalidAdapterInput(f"unsupported action id: {action_id}")
        relative_path = parameters.get("relative_path")
        encoded = parameters.get("pdf_base64")
        if not isinstance(relative_path, str) or not SAFE_PDF_NAME.fullmatch(relative_path):
            raise InvalidAdapterInput("relative_path must be a safe root-level .pdf filename")
        if relative_path.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
            raise InvalidAdapterInput("relative_path uses a reserved filename")
        if not isinstance(encoded, str):
            raise InvalidAdapterInput("pdf_base64 must be a base64 string")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InvalidAdapterInput("pdf_base64 is invalid") from exc
        if not content or len(content) > MAX_PDF_BYTES:
            raise InvalidAdapterInput("PDF content is empty or exceeds the adapter limit")
        if not content.startswith(b"%PDF-") or not content.rstrip().endswith(b"%%EOF"):
            raise InvalidAdapterInput("content does not have a PDF header and EOF marker")
        content_digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
        resource_id = f"file:{relative_path}"
        request_digest = canonical_digest(
            {
                "action_id": action_id,
                "relative_path": relative_path,
                "content_digest": content_digest,
            }
        )
        return relative_path, content, content_digest, resource_id, request_digest

    def _paths(self, relative_path: str) -> tuple[Path, Path]:
        target = self.output_root / relative_path
        marker = self.output_root / f".{relative_path}.skill0-receipt.json"
        if target.parent != self.output_root or marker.parent != self.output_root:
            raise InvalidAdapterInput("resolved output escaped the configured root")
        return target, marker

    def _consume_rate_limit(self, connection: sqlite3.Connection) -> None:
        now = float(self.clock())
        window_start = now - (now % self.window_seconds)
        row = connection.execute(
            "SELECT window_start, request_count FROM adapter_rate_windows WHERE bucket=?",
            (self.adapter_id,),
        ).fetchone()
        if row is None or float(row["window_start"]) != window_start:
            connection.execute(
                "INSERT INTO adapter_rate_windows(bucket, window_start, request_count) VALUES (?, ?, 1) "
                "ON CONFLICT(bucket) DO UPDATE SET window_start=excluded.window_start, request_count=1",
                (self.adapter_id, window_start),
            )
            return
        if int(row["request_count"]) >= self.max_requests:
            raise AdapterRateLimitExceeded(window_start + self.window_seconds - now)
        connection.execute(
            "UPDATE adapter_rate_windows SET request_count=request_count+1 WHERE bucket=?",
            (self.adapter_id,),
        )

    def _acquire_concurrency(self) -> None:
        if not self._concurrency.acquire(blocking=False):
            raise AdapterRateLimitExceeded(0.0)

    def _operation_row(self, key_digest: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM adapter_operations WHERE idempotency_key_digest=?",
            (key_digest,),
        ).fetchone()

    def _result_from_applied(
        self, row: sqlite3.Row, *, replayed: bool
    ) -> ActionResult:
        return ActionResult(
            True,
            outputs={
                "resource_id": row["resource_id"],
                "content_digest": row["content_digest"],
                "replayed": replayed,
            },
            external_resource_id=row["resource_id"],
        )

    def execute(
        self,
        action_id: str,
        parameters: dict[str, Any],
        *,
        idempotency_key: str | None,
        dry_run: bool,
    ) -> ActionResult:
        relative_path, content, content_digest, resource_id, request_digest = (
            self._prepare_request(action_id, parameters)
        )
        key_digest = self._key_digest(idempotency_key or "")
        if dry_run:
            return ActionResult(
                True,
                outputs={
                    "resource_id": resource_id,
                    "content_digest": content_digest,
                    "planned": True,
                    "replayed": False,
                },
                external_resource_id=resource_id,
            )

        self._acquire_concurrency()
        try:
            with self._lock:
                existing = self._operation_row(key_digest)
                if existing is not None:
                    if existing["request_digest"] != request_digest:
                        raise IdempotencyConflict(
                            "idempotency key is already bound to a different request"
                        )
                    reconciliation = self.reconcile(
                        action_id, parameters, idempotency_key=idempotency_key or ""
                    )
                    if reconciliation.status == ReconciliationStatus.APPLIED:
                        if existing["status"] == "prepared":
                            with self._transaction() as connection:
                                connection.execute(
                                    "UPDATE adapter_operations SET status='applied', applied_at=? "
                                    "WHERE idempotency_key_digest=?",
                                    (self._now_iso(), key_digest),
                                )
                            existing = self._operation_row(key_digest)
                            assert existing is not None
                        return self._result_from_applied(existing, replayed=True)
                    raise AdapterOutcomeUnknown(
                        f"existing idempotency claim requires reconciliation: {reconciliation.status.value}"
                    )

                with self._transaction() as connection:
                    self._consume_rate_limit(connection)
                    connection.execute(
                        "INSERT INTO adapter_operations("
                        "idempotency_key_digest, action_id, request_digest, resource_id, relative_path, "
                        "content_digest, status, prepared_at) VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?)",
                        (
                            key_digest,
                            action_id,
                            request_digest,
                            resource_id,
                            relative_path,
                            content_digest,
                            self._now_iso(),
                        ),
                    )

                target, marker = self._paths(relative_path)
                if target.exists() or marker.exists() or target.is_symlink() or marker.is_symlink():
                    raise AdapterOutcomeUnknown(
                        "output target or receipt marker already exists and was not overwritten"
                    )
                marker_payload = {
                    "schema_version": "1.0.0",
                    "adapter_id": self.adapter_id,
                    "adapter_version": self.adapter_version,
                    "action_id": action_id,
                    "idempotency_key_digest": key_digest,
                    "request_digest": request_digest,
                    "resource_id": resource_id,
                    "content_digest": content_digest,
                    "prepared_at": self._now_iso(),
                }
                with marker.open("x", encoding="utf-8", newline="\n") as handle:
                    json.dump(marker_payload, handle, sort_keys=True, separators=(",", ":"))
                    handle.flush()
                    os.fsync(handle.fileno())
                with target.open("xb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                if self.fault_injector is not None:
                    self.fault_injector("after_effect_commit")
                with self._transaction() as connection:
                    connection.execute(
                        "UPDATE adapter_operations SET status='applied', applied_at=? "
                        "WHERE idempotency_key_digest=?",
                        (self._now_iso(), key_digest),
                    )
                row = self._operation_row(key_digest)
                assert row is not None
                return self._result_from_applied(row, replayed=False)
        finally:
            self._concurrency.release()

    def _read_marker(self, path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def reconcile(
        self,
        action_id: str,
        parameters: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> ReconciliationResult:
        relative_path, _, content_digest, resource_id, request_digest = self._prepare_request(
            action_id, parameters
        )
        key_digest = self._key_digest(idempotency_key)
        row = self._operation_row(key_digest)
        if row is None:
            return ReconciliationResult(
                ReconciliationStatus.NOT_FOUND,
                resource_id,
                {"idempotency_key_digest": key_digest, "receipt_present": False},
            )
        if row["request_digest"] != request_digest or row["resource_id"] != resource_id:
            return ReconciliationResult(
                ReconciliationStatus.DIVERGED,
                row["resource_id"],
                {"reason": "request_or_resource_identity_mismatch"},
            )
        if row["status"] == "compensated":
            evidence = json.loads(row["compensation_evidence_json"] or "{}")
            quarantine_id = evidence.get("quarantine_resource_id", "")
            quarantine_path = self.output_root / str(quarantine_id).removeprefix("file:")
            if (
                quarantine_id.startswith("file:.del/")
                and quarantine_path.is_file()
                and file_digest(quarantine_path) == content_digest
            ):
                return ReconciliationResult(
                    ReconciliationStatus.COMPENSATED, resource_id, evidence
                )
            return ReconciliationResult(
                ReconciliationStatus.UNKNOWN,
                resource_id,
                {"reason": "compensation_evidence_does_not_match_recoverable_artifact"},
            )

        target, marker = self._paths(relative_path)
        target_exists = target.is_file() and not target.is_symlink()
        marker_exists = marker.is_file() and not marker.is_symlink()
        if target_exists and marker_exists:
            marker_payload = self._read_marker(marker)
            if (
                marker_payload is not None
                and marker_payload.get("idempotency_key_digest") == key_digest
                and marker_payload.get("request_digest") == request_digest
                and marker_payload.get("content_digest") == content_digest
                and file_digest(target) == content_digest
            ):
                return ReconciliationResult(
                    ReconciliationStatus.APPLIED,
                    resource_id,
                    {
                        "idempotency_key_digest": key_digest,
                        "content_digest": content_digest,
                        "receipt_marker_present": True,
                        "effect_count": 1,
                    },
                )
            return ReconciliationResult(
                ReconciliationStatus.DIVERGED,
                resource_id,
                {"reason": "artifact_or_marker_digest_mismatch"},
            )
        if not target.exists() and not marker.exists():
            return ReconciliationResult(
                ReconciliationStatus.NOT_FOUND,
                resource_id,
                {"receipt_claim_present": True, "automatic_retry_allowed": False},
            )
        return ReconciliationResult(
            ReconciliationStatus.UNKNOWN,
            resource_id,
            {
                "artifact_present": target_exists,
                "receipt_marker_present": marker_exists,
                "automatic_retry_allowed": False,
            },
        )

    def compensate(
        self,
        action_id: str,
        parameters: dict[str, Any],
        *,
        idempotency_key: str,
        dry_run: bool,
    ) -> ActionResult:
        if action_id != SUPPORTED_ACTION_ID:
            raise InvalidAdapterInput(f"unsupported compensation action id: {action_id}")
        resource_id = parameters.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id.startswith("file:"):
            raise InvalidAdapterInput("compensation requires a file: resource_id")
        compensation_key_digest = self._key_digest(idempotency_key)
        row = self.connection.execute(
            "SELECT * FROM adapter_operations WHERE resource_id=?", (resource_id,)
        ).fetchone()
        if row is None:
            raise AdapterOutcomeUnknown("compensation resource is not owned by this adapter")
        if dry_run:
            return ActionResult(
                True,
                outputs={"resource_id": resource_id, "planned_compensation": True},
                external_resource_id=resource_id,
            )

        self._acquire_concurrency()
        try:
            with self._lock:
                existing = self.connection.execute(
                    "SELECT * FROM adapter_compensations WHERE compensation_key_digest=?",
                    (compensation_key_digest,),
                ).fetchone()
                if existing is not None:
                    if existing["resource_id"] != resource_id:
                        raise IdempotencyConflict(
                            "compensation key is already bound to another resource"
                        )
                    if existing["status"] == "succeeded":
                        evidence = json.loads(existing["evidence_json"] or "{}")
                        return ActionResult(
                            True,
                            outputs={**evidence, "replayed": True},
                            external_resource_id=resource_id,
                        )
                    raise AdapterOutcomeUnknown("compensation is prepared but has no terminal receipt")

                with self._transaction() as connection:
                    self._consume_rate_limit(connection)
                    connection.execute(
                        "INSERT INTO adapter_compensations("
                        "compensation_key_digest, resource_id, status, prepared_at) "
                        "VALUES (?, ?, 'prepared', ?)",
                        (compensation_key_digest, resource_id, self._now_iso()),
                    )

                primary_key_digest = row["idempotency_key_digest"]
                target, marker = self._paths(row["relative_path"])
                if (
                    not target.is_file()
                    or target.is_symlink()
                    or file_digest(target) != row["content_digest"]
                    or not marker.is_file()
                    or marker.is_symlink()
                ):
                    raise AdapterOutcomeUnknown(
                        "compensation refused because the owned resource is not intact"
                    )
                marker_payload = self._read_marker(marker)
                if marker_payload is None or marker_payload.get(
                    "idempotency_key_digest"
                ) != primary_key_digest:
                    raise AdapterOutcomeUnknown("compensation receipt marker does not prove ownership")

                quarantine_root = self.output_root / ".del"
                if quarantine_root.exists() and (
                    not quarantine_root.is_dir() or quarantine_root.is_symlink()
                ):
                    raise AdapterOutcomeUnknown("recoverable .del sink is not a safe directory")
                quarantine_root.mkdir(exist_ok=True)
                suffix = compensation_key_digest.removeprefix("sha256:")[:12]
                quarantine_name = f"{row['relative_path']}.{suffix}"
                quarantine_marker_name = f".{row['relative_path']}.{suffix}.skill0-receipt.json"
                quarantine_path = quarantine_root / quarantine_name
                quarantine_marker = quarantine_root / quarantine_marker_name
                evidence_path = quarantine_root / f".{row['relative_path']}.{suffix}.compensation.json"
                if any(path.exists() or path.is_symlink() for path in (quarantine_path, quarantine_marker, evidence_path)):
                    raise AdapterOutcomeUnknown("recoverable compensation destination already exists")

                os.replace(target, quarantine_path)
                os.replace(marker, quarantine_marker)
                completed_at = self._now_iso()
                evidence = {
                    "original_resource_id": resource_id,
                    "content_digest": row["content_digest"],
                    "quarantine_resource_id": f"file:.del/{quarantine_name}",
                    "compensation_key_digest": compensation_key_digest,
                    "completed_at": completed_at,
                }
                with evidence_path.open("x", encoding="utf-8", newline="\n") as handle:
                    json.dump(evidence, handle, sort_keys=True, separators=(",", ":"))
                    handle.flush()
                    os.fsync(handle.fileno())
                with self._transaction() as connection:
                    evidence_json = json.dumps(
                        evidence, sort_keys=True, separators=(",", ":")
                    )
                    connection.execute(
                        "UPDATE adapter_operations SET status='compensated', compensation_evidence_json=? "
                        "WHERE idempotency_key_digest=?",
                        (evidence_json, primary_key_digest),
                    )
                    connection.execute(
                        "UPDATE adapter_compensations SET status='succeeded', evidence_json=?, completed_at=? "
                        "WHERE compensation_key_digest=?",
                        (evidence_json, completed_at, compensation_key_digest),
                    )
                return ActionResult(
                    True,
                    outputs={**evidence, "replayed": False},
                    external_resource_id=resource_id,
                )
        finally:
            self._concurrency.release()
