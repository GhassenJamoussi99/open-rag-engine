"""Provider-neutral LLM request, response and stream event types."""

from typing import Annotated, Literal

from pydantic import Field

from open_rag_engine.domain import DomainModel, NonBlankStr, Offset


class LLMRequest(DomainModel):
    system: str
    prompt: NonBlankStr
    max_tokens: Annotated[int, Field(ge=1, le=32_000)] = 1024
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.0


class LLMResponse(DomainModel):
    text: str
    model: NonBlankStr
    input_tokens: Offset
    output_tokens: Offset
    stop_reason: str | None = None


class TextDelta(DomainModel):
    """A piece of the answer while it is being generated."""

    type: Literal["text_delta"] = "text_delta"
    text: str


class StreamEnd(DomainModel):
    """The last event of a stream, carrying the complete response."""

    type: Literal["end"] = "end"
    response: LLMResponse


LLMEvent = TextDelta | StreamEnd
