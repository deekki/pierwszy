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
def load_cartons_with_weights() -> dict:
    """Return cartons with weight included {code: (w, l, h, weight)}."""
    root = _load_xml(os.path.join(DATA_DIR, 'cartons.xml'))
    cartons = {}
    for carton in root.findall('carton'):
        try:
            code = carton.get('code')
            w = int(carton.get('w'))
            length = int(carton.get('l'))
            h = int(carton.get('h'))
            weight = float(carton.get('weight', '0'))
            cartons[code] = (w, length, h, weight)
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
def load_pallets_with_weights() -> list:
    """Return list of pallets with weight info."""
    root = _load_xml(os.path.join(DATA_DIR, 'pallets.xml'))
    pallets = []
    for pallet in root.findall('pallet'):
        try:
            name = pallet.get('name')
            w = int(pallet.get('w'))
            length = int(pallet.get('l'))
            h = int(pallet.get('h'))
            weight = float(pallet.get('weight', '0'))
            pallets.append({'name': name, 'w': w, 'l': length, 'h': h, 'weight': weight})
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


def load_cartons_list() -> list:
    """Load cartons from cartons.xml as a list of dictionaries."""
    root = _load_xml(os.path.join(DATA_DIR, 'cartons.xml'))
    cartons = []
    for carton in root.findall('carton'):
        cartons.append(
            {
                'code': carton.get('code', ''),
                'w': carton.get('w', ''),
                'l': carton.get('l', ''),
                'h': carton.get('h', ''),
                'weight': carton.get('weight', ''),
            }
        )
    return cartons


def save_cartons(cartons: list) -> None:
    """Save cartons list back to cartons.xml and clear caches."""
    root = ET.Element('cartons')
    for c in cartons:
        ET.SubElement(
            root,
            'carton',
            code=c.get('code', ''),
            w=str(c.get('w', '')),
            l=str(c.get('l', '')),
            h=str(c.get('h', '')),
            weight=str(c.get('weight', '')),
        )
    tree = ET.ElementTree(root)
    tree.write(os.path.join(DATA_DIR, 'cartons.xml'), encoding='utf-8', xml_declaration=True)
    load_cartons.cache_clear()
    load_cartons_with_weights.cache_clear()


def _load_generic_materials(filename: str) -> list:
    """Helper to load material lists from XML files."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    root = _load_xml(path)
    materials = []
    for mat in root.findall('material'):
        materials.append(
            {
                'name': mat.get('name', ''),
                'quantity': mat.get('quantity', ''),
                'comment': mat.get('comment', ''),
                'weight': mat.get('weight', ''),
                'type': mat.get('type', ''),
                'supplier': mat.get('supplier', ''),
            }
        )
    return materials


def _save_generic_materials(filename: str, materials: list) -> None:
    """Helper to save material lists to XML files."""
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
            supplier=mat.get('supplier', ''),
        )
    tree = ET.ElementTree(root)
    tree.write(os.path.join(DATA_DIR, filename), encoding='utf-8', xml_declaration=True)


def load_direct_packaging() -> list:
    """Load direct packaging materials from direct_packaging.xml."""
    return _load_generic_materials('direct_packaging.xml')


def save_direct_packaging(materials: list) -> None:
    """Save direct packaging materials to direct_packaging.xml."""
    _save_generic_materials('direct_packaging.xml', materials)


def load_indirect_packaging() -> list:
    """Load indirect packaging materials from indirect_packaging.xml."""
    return _load_generic_materials('indirect_packaging.xml')


def save_indirect_packaging(materials: list) -> None:
    """Save indirect packaging materials to indirect_packaging.xml."""
    _save_generic_materials('indirect_packaging.xml', materials)


def load_auxiliary_materials() -> list:
    """Load auxiliary materials from auxiliary_materials.xml."""
    return _load_generic_materials('auxiliary_materials.xml')


def save_auxiliary_materials(materials: list) -> None:
    """Save auxiliary materials to auxiliary_materials.xml."""
    _save_generic_materials('auxiliary_materials.xml', materials)


@lru_cache(maxsize=None)
def load_slip_sheets() -> list:
    """Load slip sheet weights from slip_sheets.xml."""
    path = os.path.join(DATA_DIR, 'slip_sheets.xml')
    if not os.path.exists(path):
        return []
    root = _load_xml(path)
    weights = []
    for slip in root.findall('slip'):
        try:
            weights.append(float(slip.get('weight', '0')))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane przekładki '{slip.attrib}': {e}")
    return weights


def save_slip_sheets(weights: list) -> None:
    """Save slip sheet weights to slip_sheets.xml."""
    root = ET.Element('slip_sheets')
    for w in weights:
        ET.SubElement(root, 'slip', weight=str(w))
    tree = ET.ElementTree(root)
    tree.write(os.path.join(DATA_DIR, 'slip_sheets.xml'), encoding='utf-8', xml_declaration=True)
    load_slip_sheets.cache_clear()

