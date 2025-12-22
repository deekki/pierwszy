import os
import xml.etree.ElementTree as ET
from functools import lru_cache

from .paths import pallets_xml_path


def _load_xml(path: str) -> ET.Element:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Brak pliku: {path}")
    try:
        tree = ET.parse(path)
        return tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Niepoprawny format XML w pliku {path}: {e}")


@lru_cache(maxsize=None)
def load_pallets() -> list:
    """Zwraca listę palet w formacie [{'name':.., 'w':.., 'l':.., 'h':..}]"""
    root = _load_xml(pallets_xml_path())
    pallets = []
    for pallet in root.findall("pallet"):
        try:
            name = pallet.get("name")
            w = int(pallet.get("w"))
            length = int(pallet.get("l"))
            h = int(pallet.get("h"))
            pallets.append({"name": name, "w": w, "l": length, "h": h})
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane palety '{pallet.attrib}': {e}")
    return pallets


@lru_cache(maxsize=None)
def load_pallets_with_weights() -> list:
    """Return list of pallets with weight info."""
    root = _load_xml(pallets_xml_path())
    pallets = []
    for pallet in root.findall("pallet"):
        try:
            name = pallet.get("name")
            w = int(pallet.get("w"))
            length = int(pallet.get("l"))
            h = int(pallet.get("h"))
            weight = float(pallet.get("weight", "0"))
            pallets.append(
                {"name": name, "w": w, "l": length, "h": h, "weight": weight}
            )
        except (TypeError, ValueError) as e:
            raise ValueError(f"Niepoprawne dane palety '{pallet.attrib}': {e}")
    return pallets
