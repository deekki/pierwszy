from __future__ import annotations

from datetime import datetime


def build_packaging_test_card(data: dict) -> str:
    lines = [
        "# Karta testu opakowania",
        "",
        f"Data wygenerowania: {data.get('date') or datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Dane opakowania",
        f"- Karton: {data.get('carton_name', '')}",
        f"- Wymiary kartonu: {data.get('carton_dims', '')}",
        f"- Dane palety: {data.get('pallet_data', '')}",
        f"- Kartonów na warstwie: {data.get('cartons_per_layer', '')}",
        f"- Liczba warstw: {data.get('layers', '')}",
        f"- Kartonów na palecie: {data.get('cartons_per_pallet', '')}",
        f"- Produktów na palecie: {data.get('products_per_pallet', '')}",
        f"- Wysokość palety: {data.get('pallet_height', '')}",
        f"- Masa palety: {data.get('pallet_mass', '')}",
        f"- Układ paletyzacji: {data.get('layout', '')}",
        f"- Ostrzeżenia: {data.get('warnings', '') or 'brak'}",
        "",
        "## Checklista operatora",
    ]
    checks = ["produkt mieści się w kartonie", "karton zamyka się poprawnie", "karton nie odkształca się nadmiernie", "etykieta/kod są czytelne", "układ na palecie zgodny z rysunkiem", "paleta stabilna po owinięciu", "brak uszkodzeń po próbie transportowej/wewnętrznej"]
    lines += [f"- [ ] {c}" for c in checks]
    lines += ["", "## Wynik testu", "- [ ] OK", "- [ ] NOK", "- [ ] warunkowo OK", "", "## Uwagi", "", "", "## Decyzja końcowa", ""]
    return "\n".join(lines)
