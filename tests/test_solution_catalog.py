from palletizer_core.solutions import Solution, build_solution_catalog, ui_model_from_catalog


def make_solution(key, kind, cartons, stability, signature):
    return Solution(
        key=key,
        display=key,
        kind=kind,
        layout=[(0.0, 0.0, 1.0, 1.0)],
        metrics={"cartons": float(cartons), "stability": float(stability)},
        signature=signature,
    )


def test_dedupe_prefers_standard_over_extra_for_same_signature():
    standard = make_solution("mixed", "standard", 10, 0.5, ("sig",))
    extra = make_solution("extra_1", "extra", 12, 0.9, ("sig",))

    catalog = build_solution_catalog([extra, standard])

    assert [solution.key for solution in catalog.solutions] == ["mixed"]


def test_catalog_has_unique_keys_and_unique_signatures():
    solutions = [
        make_solution("dynamic", "standard", 12, 0.6, ("sig1",)),
        make_solution("dynamic_alt", "extra", 11, 0.7, ("sig1",)),
        make_solution("pinwheel", "standard", 8, 0.4, ("sig2",)),
    ]

    catalog = build_solution_catalog(solutions)

    keys = [solution.key for solution in catalog.solutions]
    signatures = [solution.signature for solution in catalog.solutions]
    assert len(keys) == len(set(keys))
    assert len(signatures) == len(set(signatures))


def test_sorting_default_max_cartons():
    low_cartons = make_solution("low", "extra", 8, 0.99, ("low",))
    high_cartons = make_solution("high", "extra", 12, 0.2, ("high",))

    catalog = build_solution_catalog([low_cartons, high_cartons])

    assert [solution.key for solution in catalog.solutions] == ["high", "low"]


def test_ui_model_matches_catalog_order():
    first = make_solution("first", "standard", 10, 0.5, ("first",))
    second = make_solution("second", "standard", 9, 0.5, ("second",))

    catalog = build_solution_catalog([first, second])

    dropdown, rows = ui_model_from_catalog(catalog)
    assert dropdown == [solution.display for solution in catalog.solutions]
    assert rows == [solution.key for solution in catalog.solutions]
