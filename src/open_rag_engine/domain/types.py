"""Reusable constrained field types shared by the domain objects."""

from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


NonBlankStr = Annotated[str, AfterValidator(_not_blank)]
"""A string with at least one non-whitespace character."""

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]
"""A lowercase label such as a document type or access tag: `contract`, `nda`, `legal-eu`."""

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
"""A lowercase hex SHA-256 digest."""

StrictCount = Annotated[int, Field(strict=True, ge=1)]
"""A positive integer; bools, strings and floats are rejected."""

Offset = Annotated[int, Field(strict=True, ge=0)]
"""A character offset into a document's full parsed text, counted in Unicode code points."""

PageNumber = Annotated[int, Field(strict=True, ge=1)]
"""A 1-based page number."""
