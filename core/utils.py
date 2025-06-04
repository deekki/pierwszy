from tkinter import messagebox

def validate_number(value: str) -> bool:
    """Validate numeric entry using comma as decimal separator."""
    if value == "":
        return True
    if "." in value:
        messagebox.showwarning("B\u0142\u0105d", "U\u017cyj przecinka jako separatora dziesi\u0119tnego.")
        return False
    try:
        num = float(value.replace(",", "."))
    except ValueError:
        return False
    if num < 0:
        messagebox.showwarning("B\u0142\u0105d", "Warto\u015b\u0107 nie mo\u017ce by\u0107 ujemna.")
        return False
    return True

def parse_dim(value: str) -> float:
    """Parse dimension from string using comma as decimal separator."""
    if "." in value:
        messagebox.showwarning("B\u0142\u0105d", "U\u017cyj przecinka jako separatora dziesi\u0119tnego.")
        return 0.0
    try:
        num = float(value.replace(",", "."))
    except ValueError:
        messagebox.showwarning("B\u0142\u0105d", "Wprowadzono niepoprawn\u0105 warto\u015b\u0107. U\u017cyto 0.")
        return 0.0
    if num < 0:
        messagebox.showwarning("B\u0142\u0105d", "Warto\u015b\u0107 nie mo\u017ce by\u0107 ujemna. U\u017cyto 0.")
        return 0.0
    return num
