import os
import xml.etree.ElementTree as ET
from functools import lru_cache

from .cache import clear_carton_cache
from .paths import cartons_xml_path


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
    root = _load_xml(cartons_xml_path())
    cartons = {}
    for carton in root.findall("carton"):
        try:
            code = carton.get("code")
            w = int(carton.get("w"))
            length = int(carton.get("l"))
            h = int(carton.get("h"))
            cartons[code] = (w, length, h)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane kartonu '{carton.attrib}': {e}")
    return cartons


@lru_cache(maxsize=None)
def load_cartons_with_weights() -> dict:
    """Return cartons with weight included {code: (w, l, h, weight)}."""
    root = _load_xml(cartons_xml_path())
    cartons = {}
    for carton in root.findall("carton"):
        try:
            code = carton.get("code")
            w = int(carton.get("w"))
            length = int(carton.get("l"))
            h = int(carton.get("h"))
            weight = float(carton.get("weight", "0"))
            cartons[code] = (w, length, h, weight)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane kartonu '{carton.attrib}': {e}")
    return cartons


def load_cartons_list() -> list:
    """Load cartons from cartons.xml as a list of dictionaries."""
    root = _load_xml(cartons_xml_path())
    cartons = []
    for carton in root.findall("carton"):
        cartons.append(
            {
                "code": carton.get("code", ""),
                "w": carton.get("w", ""),
                "l": carton.get("l", ""),
                "h": carton.get("h", ""),
                "weight": carton.get("weight", ""),
            }
        )
    return cartons


def save_cartons(cartons: list) -> None:
    """Save cartons list back to cartons.xml and clear caches."""
    root = ET.Element("cartons")
    for carton in cartons:
        ET.SubElement(
            root,
            "carton",
            code=carton.get("code", ""),
            w=str(carton.get("w", "")),
            l=str(carton.get("l", "")),
            h=str(carton.get("h", "")),
            weight=str(carton.get("weight", "")),
        )
    tree = ET.ElementTree(root)
    tree.write(cartons_xml_path(), encoding="utf-8", xml_declaration=True)
    clear_carton_cache()
