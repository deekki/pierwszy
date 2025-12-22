MM = float
KG = float


def parse_float(value: str) -> float:
    text = value.strip()
    if not text:
        raise ValueError("empty input")
    text = text.replace(",", ".")
    return float(text)


def format_float(value: float, ndigits: int = 2) -> str:
    return f"{value:.{ndigits}f}"
