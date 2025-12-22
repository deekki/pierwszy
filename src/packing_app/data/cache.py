def clear_carton_cache() -> None:
    from .cartons_repo import load_cartons, load_cartons_with_weights

    load_cartons.cache_clear()
    load_cartons_with_weights.cache_clear()


def clear_slip_sheet_cache() -> None:
    from .materials_repo import load_slip_sheets

    load_slip_sheets.cache_clear()
