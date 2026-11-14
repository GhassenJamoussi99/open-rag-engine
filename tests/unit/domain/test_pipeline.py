import pytest
from pydantic import ValidationError

from open_rag_engine.domain import PipelineState, StageTiming, evolve
from tests.factories import make_answer, make_context, make_query, make_scored_chunk


def _initial_state() -> PipelineState:
    return PipelineState(query=make_query(), context=make_context())


def test_starts_with_only_query_and_context() -> None:
    state = _initial_state()

    assert state.candidates == ()
    assert state.ranked == ()
    assert state.prompt is None
    assert state.answer is None
    assert state.degraded == ()
    assert state.timings_ms == {}


def test_stage_update_returns_new_state_and_keeps_the_old_one() -> None:
    before = _initial_state()
    hits = [make_scored_chunk(0.9), make_scored_chunk(0.7)]

    after = evolve(before, candidates=hits)

    assert len(after.candidates) == 2
    assert isinstance(after.candidates, tuple)
    assert before.candidates == ()


def test_records_timings_per_stage() -> None:
    state = evolve(
        _initial_state(),
        timings=(StageTiming(stage="embed", ms=9.0), StageTiming(stage="retrieve", ms=14.5)),
    )

    assert state.timings_ms == {"embed": 9.0, "retrieve": 14.5}


def test_rejects_duplicate_stage_timings() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        evolve(
            _initial_state(),
            timings=(StageTiming(stage="embed", ms=1.0), StageTiming(stage="embed", ms=2.0)),
        )


def test_rejects_negative_timing() -> None:
    with pytest.raises(ValidationError, match="ms"):
        StageTiming(stage="embed", ms=-1.0)


def test_holds_final_answer() -> None:
    state = evolve(_initial_state(), prompt="[1] ...", answer=make_answer())

    assert state.answer is not None
    assert state.answer.refused is False
