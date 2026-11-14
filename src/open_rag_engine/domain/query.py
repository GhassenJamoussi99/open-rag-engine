"""What the user asked, and who is asking."""

from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field, StringConstraints

from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.types import NonBlankStr, Slug

MAX_QUESTION_CHARS = 2000


class QueryOptions(DomainModel):
    top_k: Annotated[int, Field(strict=True, ge=1, le=50)] = 8


class Query(DomainModel):
    """A question plus the user's filters. Surrounding whitespace is stripped."""

    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)
    ]
    doc_types: tuple[Slug, ...] = ()
    options: QueryOptions = Field(default_factory=QueryOptions)


class RequestContext(DomainModel):
    """Who is asking, under which tenant and access tags.

    `tenant_id` has no default, so no request can run without one. Only the auth
    middleware (Phase 4) and the eval runner build contexts; Phase 1 uses one default
    tenant.
    """

    request_id: UUID = Field(default_factory=uuid4)
    trace_id: NonBlankStr = Field(default_factory=lambda: uuid4().hex)
    tenant_id: NonBlankStr
    principal_id: str | None = None
    access_tags: tuple[Slug, ...] = ()
    debug: bool = False
