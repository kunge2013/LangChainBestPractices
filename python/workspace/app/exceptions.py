"""
Custom exception classes for the ledger subsystem.
"""
from __future__ import annotations


class LedgerError(Exception):
    """Base exception for ledger domain errors."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class T0SourceError(LedgerError):
    pass


class LedgerItemError(LedgerError):
    pass


class ClaimError(LedgerError):
    pass


class TempClaimError(LedgerError):
    pass


class WriteOffError(LedgerError):
    pass


class ReverseError(LedgerError):
    pass


class ReportError(LedgerError):
    pass


class DiffError(LedgerError):
    pass
