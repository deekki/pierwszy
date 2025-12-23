from __future__ import annotations

from typing import Callable

from packing_app.gui.pattern_apply_debouncer import PatternApplyDebouncer


class FakeScheduler:
    def __init__(self) -> None:
        self._next_id = 0
        self._callbacks: dict[int, Callable[[], None]] = {}

    def schedule(self, callback: Callable[[], None]) -> int:
        self._next_id += 1
        self._callbacks[self._next_id] = callback
        return self._next_id

    def cancel(self, schedule_id: int) -> None:
        self._callbacks.pop(schedule_id, None)

    def run_all(self) -> None:
        callbacks = list(self._callbacks.items())
        self._callbacks.clear()
        for _, callback in callbacks:
            callback()


def test_debouncer_last_request_wins() -> None:
    scheduler = FakeScheduler()
    calls: list[tuple[str, bool]] = []

    debouncer = PatternApplyDebouncer(
        scheduler.schedule, scheduler.cancel, lambda key, force: calls.append((key, force))
    )

    debouncer.request("A", force=False)
    debouncer.request("B", force=True)

    scheduler.run_all()

    assert calls == [("B", True)]


def test_debouncer_deduplicates_same_key() -> None:
    scheduler = FakeScheduler()
    calls: list[tuple[str, bool]] = []

    debouncer = PatternApplyDebouncer(
        scheduler.schedule, scheduler.cancel, lambda key, force: calls.append((key, force))
    )

    debouncer.request("A", force=False)
    debouncer.request("A", force=False)

    scheduler.run_all()

    assert calls == [("A", False)]


def test_debouncer_cancel_prevents_apply() -> None:
    scheduler = FakeScheduler()
    calls: list[tuple[str, bool]] = []

    debouncer = PatternApplyDebouncer(
        scheduler.schedule, scheduler.cancel, lambda key, force: calls.append((key, force))
    )

    debouncer.request("A", force=False)
    scheduler.cancel(debouncer._after_id)

    scheduler.run_all()

    assert calls == []
