from packing_app.core.carton_selection import best_product_fit, rank_cartons
from packing_app.core.test_card import build_packaging_test_card


def test_best_product_fit_checks_orientations():
    count, eff, orientation = best_product_fit((120, 80, 50), (70, 40, 30), 0)
    assert count >= 4
    assert sorted(orientation) == [30, 40, 70]
    assert eff > 0


def test_rank_cartons_sorts_by_products_per_pallet():
    results = rank_cartons({"A": (200, 200, 100), "B": (400, 400, 200)}, [{"w": 800, "l": 1200, "h": 144, "weight": 20}], product_dims=(100, 100, 50))
    assert results[0].products_per_pallet >= results[1].products_per_pallet
    assert results[0].status


def test_packaging_test_card_contains_operator_checklist():
    card = build_packaging_test_card({"carton_name": "C1", "cartons_per_layer": 10})
    assert "# Karta testu opakowania" in card
    assert "produkt mieści się w kartonie" in card
    assert "## Wynik testu" in card
