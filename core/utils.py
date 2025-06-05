import os
import xml.etree.ElementTree as ET
from functools import lru_cache

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'packing_app', 'data'
)


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
            length = int(carton.get('l'))
            h = int(carton.get('h'))
            cartons[code] = (w, length, h)
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
            length = int(pallet.get('l'))
            h = int(pallet.get('h'))
            pallets.append({'name': name, 'w': w, 'l': length, 'h': h})
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane palety '{pallet.attrib}': {e}")
    return pallets


@lru_cache(maxsize=None)
def load_materials() -> dict:
    """Zwraca słownik materiałów {nazwa: waga_na_m} """
    root = _load_xml(os.path.join(DATA_DIR, 'materials.xml'))
    materials = {}
    for mat in root.findall('material'):
        try:
            name = mat.get('name')
            weight = float(mat.get('weight_per_m', '0'))
            materials[name] = weight
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane materiału '{mat.attrib}': {e}")
    return materials


def load_packaging_materials() -> list:
    """Load packaging materials from packaging_materials.xml."""
    path = os.path.join(DATA_DIR, 'packaging_materials.xml')
    if not os.path.exists(path):
        return []
    root = _load_xml(path)
    materials = []
    for mat in root.findall('material'):
        materials.append({
            'name': mat.get('name', ''),
            'quantity': mat.get('quantity', ''),
            'comment': mat.get('comment', ''),
            'weight': mat.get('weight', ''),
            'type': mat.get('type', ''),
            'supplier': mat.get('supplier', '')
        })
    return materials


def save_packaging_materials(materials: list) -> None:
    """Save packaging materials to packaging_materials.xml."""
    root = ET.Element('materials')
    for mat in materials:
        ET.SubElement(
            root,
            'material',
            name=mat.get('name', ''),
            quantity=mat.get('quantity', ''),
            comment=mat.get('comment', ''),
            weight=mat.get('weight', ''),
            type=mat.get('type', ''),
            supplier=mat.get('supplier', '')
        )
    tree = ET.ElementTree(root)
    tree.write(os.path.join(DATA_DIR, 'packaging_materials.xml'), encoding='utf-8', xml_declaration=True)
