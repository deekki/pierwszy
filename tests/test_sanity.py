from palletizer_core.models import Carton, Pallet
from palletizer_core.sanity import DEFAULT_SANITY_POLICY, is_sane, sanity_flags


def test_single_carton_columns_flagged():
    layout = [
        (0.0, 0.0, 10.0, 10.0),
        (20.0, 0.0, 10.0, 10.0),
        (40.0, 0.0, 10.0, 10.0),
        (60.0, 0.0, 10.0, 10.0),
    ]
    carton = Carton(width=10.0, length=10.0)
    pallet = Pallet(width=100.0, length=100.0)

    flags = sanity_flags(layout, carton, pallet, DEFAULT_SANITY_POLICY)

    assert "single_carton_column" in flags
    assert not is_sane(layout, carton, pallet, DEFAULT_SANITY_POLICY)
