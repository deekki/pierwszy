import tkinter as tk
from tkinter import messagebox

__all__ = ["parse_dim"]

def parse_dim(var: tk.StringVar) -> float:
    """Safely parse dimension from a Tk variable."""
    try:
        val = float(var.get().replace(",", "."))
        return max(0.0, val)
    except Exception:
        messagebox.showwarning("Błąd", "Wprowadzono niepoprawną wartość. Użyto 0.")
        return 0.0
