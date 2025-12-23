from __future__ import annotations

from collections.abc import Callable
from typing import Any


class PatternApplyDebouncer:
    def __init__(
        self,
        schedule: Callable[[Callable[[], None]], Any],
        cancel: Callable[[Any], None],
        apply: Callable[[str, bool], None],
    ) -> None:
        self._schedule = schedule
        self._cancel = cancel
        self._apply = apply
        self._after_id: Any | None = None
        self._pending_key: str | None = None
        self._pending_force = False

    def request(self, key: str, force: bool) -> None:
        if not key:
            return
        self._pending_key = key
        self._pending_force = self._pending_force or force
        if self._after_id is not None:
            self._cancel(self._after_id)
        self._after_id = self._schedule(self.flush)

    def flush(self) -> None:
        self._after_id = None
        key = self._pending_key
        force = self._pending_force
        self._pending_key = None
        self._pending_force = False
        if key is None:
            return
        self._apply(key, force)
