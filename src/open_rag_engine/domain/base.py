"""Base class and update helper shared by every domain object."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Frozen, strict-shaped base: no unknown fields, no NaN or infinity, no mutation."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


def evolve[M: DomainModel](model: M, /, **changes: object) -> M:
    """Return a validated copy of `model` with `changes` applied.

    Pydantic's `model_copy(update=...)` skips validation, so a pipeline stage could
    build an invalid object by accident. This helper re-runs every validator, rejects
    unknown field names, and reuses nested objects as they are, since they are frozen.
    """
    return type(model).model_validate({**dict(model), **changes})
