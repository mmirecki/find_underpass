from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from time import time
from traceback import format_list
from typing import Iterable

import shapefile
from shp_utils import ShpFieldMapper

from shapely import LineString, Point, MultiPoint
import shapely as sh

from spatialindex import RTreeSpatialIndex

road_filter = {
    'primary',
    'primary_link',
    'secondary'
    'secondary_link',
    'tertiary',
    'tertiary_link',
    'motorway',
    'motorway_link',
    'trunk',
    'trunk_link',
    'living_street',
    'residential',
    # 'service',
    # 'busway',
    # 'unclassified',
    # 'unknown',
}


@dataclass
class Road:
    geom: LineString
    osm_id: int
    category: str
    layer: int
    bridge: bool

    def __hash__(self):
        return hash(self.osm_id)

    def __eq__(self, other):
        if not isinstance(other, Road):
            return False
        return self.osm_id == other.osm_id

    @property
    def is_road(self) -> bool:
        return self.category in road_filter


@dataclass
class GradeCrossing:
    geom: Point
    underpass: Road
    overpass: Road
    comment: str


@dataclass
class Dataset:
    roads: list[Road]
    index: RTreeSpatialIndex


def find_underpass(dataset: Dataset) -> list[GradeCrossing]:
    nr = 0
    result: list[GradeCrossing] = []
    for road in dataset.roads:
        nr += 1
        if nr % 10000 == 0:
            print(nr)

        if not road.is_road:
            continue

        candidate_roads = dataset.index.get_items(road.geom.coords, 0)
        for cr in candidate_roads:
            if cr is road:
                continue

            if cr.layer <= road.layer:
                continue

            if not sh.intersects(road.geom, cr.geom):
                continue

            if sh.touches(road.geom, cr.geom):
                continue

            intersection_result = sh.intersection(road.geom, cr.geom)
            # assert intersection_result.geom_type == 'Point', f'type={intersection_result.geom_type} for osm_id={road.osm_id}, {cr.osm_id}'

            if intersection_result.geom_type == 'MultiPoint':
                points = []
                for geom in intersection_result.geoms:
                    if geom.coords[0] != road.geom.coords[0] and geom.coords[0] != road.geom.coords[-1]:
                        points.append(geom)
                nr_points = len(points)
                if nr_points == 1:
                    intersection_result = points[0]
                elif nr_points == 0:
                    continue
                else:
                    for pt in points:
                        result.append(GradeCrossing(Point(pt), road, cr, 'multiple intersection points'))
                    continue

            elif intersection_result.geom_type != 'Point':
                print(f'bad result for {road.category}-{cr.category}: {intersection_result}')
                continue

            comment = ''
            if not cr.bridge:
                comment = 'not a bridge'



            result.append(GradeCrossing(intersection_result, road, cr, comment))

    return result


def save_result(result: Iterable[GradeCrossing], filename: Path):
    with shapefile.Writer(str(filename), shapeType=shapefile.POINT) as writer:
        writer.field('osm_id_l', 'N', 20)
        writer.field('osm_id_h', 'N', 20)
        writer.field('comment', 'C', 50)
        for pt in result:
            writer.point(*pt.geom.coords[0])
            writer.record(pt.underpass.osm_id, pt.overpass.osm_id, pt.comment)


def load_data(folder: Path) -> Dataset:
    roads_file = folder / 'gis_osm_roads_free_1.shp'
    rails_file = folder / 'gis_osm_railways_free_1.shp'

    road_index = RTreeSpatialIndex()
    roads = []

    categories = set()
    with shapefile.Reader(str(roads_file)) as reader:
        mapper = ShpFieldMapper(reader)
        for row in reader:
            rec = mapper.make_record(row)
            road_geom = LineString(row.shape.points)
            sh.prepare(road_geom)
            road = Road(road_geom,
                        int(rec['osm_id']),
                        rec['fclass'],
                        int(rec['layer']),
                        rec['bridge'] == 'T')
            roads.append(road)
            categories.add(road.category)
            road_index.add_item(road.geom.coords, road)

    nr_rails = 0
    with shapefile.Reader(str(rails_file)) as reader:
        for row in reader:
            nr_rails += 1
            rail_geom = LineString(row.shape.points)
            sh.prepare(road_geom)
            rail = Road(rail_geom,
                        int(rec['osm_id']),
                        rec['fclass'],
                        rec['layer'],
                        rec['bridge'] == 'T')

            road_index.add_item(rail_geom.coords, rail)

    print(f'read {len(roads)} roads, {nr_rails} rails')
    print(categories)

    return Dataset(roads, road_index)


def main():
    #folder = Path(r'/Users/mcuprjak/Downloads/scotland-latest-free.shp')
    folder = Path(r'/Users/marcin.mirecki/go/src/github.com/cuprjakm/find_underpass/shp/wales-latest-free.shp')
    # folder = Path(r'/Users/mcuprjak/Downloads/england-latest-free.shp')

    start_total = time()
    dataset = load_data(folder)
    start = time()
    road_upass = find_underpass(dataset)
    print(f'found {len(road_upass)} road underpass')
    print(f'calculation time: {time() - start:.2f} s')

    save_result(road_upass, folder / 'result.shp')
    print(f'total time: {time() - start_total:.2f} s')


if __name__ == '__main__':
    main()
