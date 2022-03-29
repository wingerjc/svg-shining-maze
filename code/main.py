

import io
import json
from typing import Any, Dict, List 

table_offset = 3

file_tag = """
<svg version="1.1"
     width="{w}" height="{h}"
     xmlns="http://www.w3.org/2000/svg">

    {body}
</svg>
"""

class Thickness(object):
    def __init__(
        self,
        min: float,
        max: float,
        nom: float,
    ) -> None:
        self.min = min
        self.max = max
        self.nom = nom


class NodeSpec(object):
    def __init__(
        self,
        height: float,
        width: float,
    ) -> None:
        self.height = height
        self.width = width

class Material(object):
    def __init__(
        self,
        unit: str,
        thickness: Dict[str,float],
        kerf: float,
        min_part: float,
        min_feature: float,
        min_engraving: float,
        node: Dict[str, float],
        corner_radius: float,
        note: str,
    ) -> None:
        self.unit = unit
        self.thickness = Thickness(**thickness)
        self.kerf = kerf
        self.min_part = min_part
        self.min_feature = min_feature
        self.min_engraving = min_engraving
        self.node = NodeSpec(**node)
        self.corner_radius = corner_radius
        self.note = note


class MapSize(object):
    def __init__(
        self,
        w: float,
        l: float
    ) -> None:
        self.w = w
        self.l = l

class MapCenter(object):
    def __init__(
        self,
        l: str,
        r: str,
        t: str,
        b: str,
        w_door: str,
        dividers: int,
    ) -> None:
        self.l = l,
        self.r = r,
        self.t = t,
        self.b = b
        self.w_door = w_door
        self.dividers = dividers

class MapBorder(object):
    def __init__(
        self,
        w_door: str,
        w_tower: int,
        l_tower: int,
        w_lamps: int,
        l_lamps: int,
    ) -> None:
        self.w_door = w_door
        self.w_tower = w_tower
        self.l_tower = l_tower
        self.w_lamps = w_lamps
        self.l_lamps = l_lamps

class MapWall(object):
    def __init__(
        self,
        start: str,
        end: str,
        row: str="",
        col: str="",
    ) -> None:
        self.start = start
        self.end = end
        self.row = row
        self.col = col

class Map(object):
    def __init__(
        self,
        hall_ratio: float,
        size: Dict[str,float],
        border: Dict[str,Any],
        center: Dict[str,Any],
        walls: Dict[str, List[Dict[str,str]]],
    ) -> None:
        self.hall_ratio = hall_ratio
        self.size = MapSize(**size)
        self.border = MapBorder(**border)
        self.center = MapCenter(**center)
        self.rows = [MapWall(**w) for w in walls["e-w"]]
        self.cols = [MapWall(**w) for w in walls["n-s"]]

class Provider(object):
    def __init__(
        self,
        cut_color: str,
        line_color: str,
        area_color: str,
        line_w: float,
    ) -> None:
        self.cut_color = cut_color
        self.line_color = line_color
        self.area_color = area_color
        self.line_w = line_w

class SVGMaze(object):
    def __init__(
        self,
        map: Map,
        material: Material,
        provider: Provider
    ) -> None:
        self.map = map
        self.material = material
        self.provider = provider

    def write_file(self):
        width = self.material.thickness.nom * ((2 * table_offset) + self.map.size.w + ((self.map.size.w - 1) * self.map.hall_ratio))
        length = self.material.thickness.nom * ((2 * table_offset) + self.map.size.l + ((self.map.size.l - 1) * self.map.hall_ratio))

        body = """
        <rect x="9" y="9" width="15" height="3"
        fill="none" stroke="blue" stroke-width="0.1"/>
        """
        print(file_tag.format(
            unit=self.material.unit,
            w=length,
            h=width,
            body=body,
        ))


map = Map(**json.load(io.FileIO("./data/patterns/test.json")))
material = Material(**json.load(io.FileIO("./data/ponoko/mat/acr3.json")))
provider = Provider(**json.load(io.FileIO("./data/ponoko/provider.json")))

maze = SVGMaze(map, material, provider)
maze.write_file()
