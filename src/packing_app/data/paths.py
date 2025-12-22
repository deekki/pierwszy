import os

DATA_DIR = os.path.join(os.path.dirname(__file__))


def data_dir() -> str:
    return DATA_DIR


def cartons_xml_path() -> str:
    return os.path.join(DATA_DIR, "cartons.xml")


def pallets_xml_path() -> str:
    return os.path.join(DATA_DIR, "pallets.xml")


def materials_xml_path() -> str:
    return os.path.join(DATA_DIR, "materials.xml")
