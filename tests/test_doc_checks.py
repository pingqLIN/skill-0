"""Regression tests for repo-local documentation validation helpers."""

from tools import check_doc_status_markers, check_shared_docs


def test_doc_status_markers_check_passes_on_repo_baseline():
    assert check_doc_status_markers.main() == 0


def test_shared_docs_check_passes_on_repo_baseline():
    assert check_shared_docs.main() == 0
