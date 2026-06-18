"""Typed external-fetch error, mirroring legacy ExternalFetchError{kind}."""
from __future__ import annotations

from typing import Literal

ErrorKind = Literal["timeout", "http", "network", "blocked"]


class ExternalFetchError(Exception):
    def __init__(
        self,
        kind: ErrorKind,
        message: str,
        *,
        host: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.host = host
        self.status = status

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        bits = [f"[{self.kind}]"]
        if self.host:
            bits.append(self.host)
        if self.status:
            bits.append(f"HTTP {self.status}")
        bits.append(super().__str__())
        return " ".join(bits)


class CircuitOpenError(ExternalFetchError):
    def __init__(self, host: str) -> None:
        super().__init__("blocked", f"circuit open for {host}", host=host)
