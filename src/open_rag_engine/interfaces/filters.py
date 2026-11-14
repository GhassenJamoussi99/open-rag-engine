"""Search filters. Built only from a RequestContext, so the tenant can't be forgotten."""

from open_rag_engine.domain import DomainModel, NonBlankStr, Query, RequestContext, Slug


class SearchFilters(DomainModel):
    tenant_id: NonBlankStr
    access_tags: tuple[Slug, ...] = ()
    doc_types: tuple[Slug, ...] = ()


def build_filters(context: RequestContext, query: Query) -> SearchFilters:
    """Combine who is asking (tenant, access tags) with what they asked for (doc types)."""
    return SearchFilters(
        tenant_id=context.tenant_id,
        access_tags=context.access_tags,
        doc_types=query.doc_types,
    )
