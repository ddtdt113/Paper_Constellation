"""Curated constellations shipped with the app."""
import json
from importlib import resources

from ..model import Graph

# file name -> (Korean title, English title)
CATALOG = {"gaussian-splatting.json": ("Gaussian Splatting 성도", "Gaussian Splatting constellation")}


def load(name: str = "gaussian-splatting.json") -> Graph:
    text = resources.files(__name__).joinpath(name).read_text(encoding="utf-8")
    return Graph.from_dict(json.loads(text))
