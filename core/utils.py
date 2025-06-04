import os
import xml.etree.ElementTree as ET
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def _load_xml(path: str) -> ET.Element:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Brak pliku: {path}")
    try:
        tree = ET.parse(path)
        return tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Niepoprawny format XML w pliku {path}: {e}")


@lru_cache(maxsize=None)
def load_cartons() -> dict:
    """Zwraca słownik kartonów {kod: (w, l, h)}."""
    root = _load_xml(os.path.join(DATA_DIR, 'cartons.xml'))
    cartons = {}
    for carton in root.findall('carton'):
        try:
            code = carton.get('code')
            w = int(carton.get('w'))
            l = int(carton.get('l'))
            h = int(carton.get('h'))
            cartons[code] = (w, l, h)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane kartonu '{carton.attrib}': {e}")
    return cartons


@lru_cache(maxsize=None)
def load_pallets() -> list:
    """Zwraca listę palet w formacie [{'name':.., 'w':.., 'l':.., 'h':..}]"""
    root = _load_xml(os.path.join(DATA_DIR, 'pallets.xml'))
    pallets = []
    for pallet in root.findall('pallet'):
        try:
            name = pallet.get('name')
            w = int(pallet.get('w'))
            l = int(pallet.get('l'))
            h = int(pallet.get('h'))
            pallets.append({'name': name, 'w': w, 'l': l, 'h': h})
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane palety '{pallet.attrib}': {e}")
    return pallets
