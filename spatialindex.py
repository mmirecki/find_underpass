"""a spatial grid for quick spatial search"""
from collections import defaultdict
from typing import Any, Set, Tuple, Dict, Sequence
from rtree.index import Index

import math
TCoord = tuple[float, float]
TCoordSequence = Sequence[TCoord]

class SimpleSpatialGrid:
    """a class representing spatial grid in metric coordinate system
    implemented with tiles (cells)"""

    def __init__(self, cellsize: float) -> None:
        self.cells: Dict[Tuple[int, int], Set[Any]] = defaultdict(set)
        self._cell_size = cellsize

    def _key(self, x: float, y: float) -> Tuple[int, int]:
        return math.floor(x / self._cell_size), math.floor(y / self._cell_size)

    def _add(self, x: float, y: float, item: Any):
        i_x, i_y = self._key(x, y)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                self.cells[(i_x + i, i_y + j)].add(item)

    def _get(self, x: float, y: float) -> Set[Any]:
        key = self._key(x, y)
        return self.cells[key]

    def add_item(self, coords: TCoordSequence, item: Any) -> None:
        """adds an item to the spatial grid
        coords - coordinates used for spatial index
        item - item to be indexed
        """
        for coord in coords:
            self._add(coord[0], coord[1], item)

    def get_items(self, coords: TCoordSequence) -> Set[Any]:
        """gets an item based on its coordinates
        coords - coordinates used for spatial index
        :return set of found items
        """
        result = set()
        for coord in coords:
            result.update(self._get(*coord))

        return result

    def contains(self, x: float, y: float) -> bool:
        """checks if given coordinate is indexed in the grid"""
        return self._key(x, y) in self.cells


class RTreeSpatialIndex:
    """a class representing spatial grid in metric coordinate system, implemented with RTree"""
    next_idx = 1

    def __init__(self) -> None:
        self._index = Index()
        self._obj_by_idx: dict[int, Any] = {}

    def add_item(self, coords: TCoordSequence, item: Any) -> None:
        """adds an item to the spatial grid
        coords - coordinates used for spatial index
        item - item to be indexed
        """

        xx, yy = list(zip(*coords))
        bbox = min(xx), min(yy), max(xx), max(yy)
        self._index.add(self.next_idx, bbox)
        self._obj_by_idx[self.next_idx] = item
        self.next_idx += 1

    def get_items(self, coords: TCoordSequence, buffer_size: float) -> Set[Any]:
        """gets an item based on its coordinates
        coords - coordinates used for spatial index
        buffer_size - the search buffer indicating how far from the coords' bbox the item should be looked for
        :return set of found items
        """
        result = set()
        xx, yy = list(zip(*coords))
        # search within 'cellsize; from the coords
        cs = buffer_size
        bbox = min(xx) - cs, min(yy) - cs, max(xx) + cs, max(yy) + cs
        for idx in self._index.intersection(bbox):
            result.add(self._obj_by_idx[idx])

        return result
