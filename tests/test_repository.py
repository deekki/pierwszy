from packing_app.data import repository


def test_repository_loads_xml_lists():
    assert repository.load_cartons()
    assert repository.load_pallets()
    assert repository.load_materials()
