"""Production adapters remain feature-gated and individually certified."""

from .local_pdf import LocalPdfFilesystemAdapter

__all__ = ["LocalPdfFilesystemAdapter"]
