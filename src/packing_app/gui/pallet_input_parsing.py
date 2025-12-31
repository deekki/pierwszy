import logging
from typing import Callable

import tkinter as tk
from tkinter import messagebox

from palletizer_core.units import parse_float

logger = logging.getLogger(__name__)


def parse_dim(
    var: tk.Variable | str,
    *,
    field: str = "",
    on_error: Callable[[str], None] | None = None,
) -> float:
    """Parse a dimensional value from a Tk variable or string.

    If parsing fails, the value ``0.0`` is returned. When ``on_error`` is
    provided, it is called with the field name instead of showing a warning
    popup, enabling inline validation.
    """

    try:
        raw_value = var.get() if hasattr(var, "get") else var
        val = parse_float(raw_value)
        return max(0, val)
    except Exception:
        if on_error is not None:
            try:
                on_error(field)
            except Exception:
                logger.exception("parse_dim error callback failed")
        else:
            messagebox.showwarning("Błąd", "Wprowadzono niepoprawną wartość. Użyto 0.")
        return 0.0
