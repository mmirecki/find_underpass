"""
this module provides utilities for working with shapefiles
"""

from typing import Union, Sequence

from shapefile import ShapeRecord


class ShpFieldMapper:
    """helper in mapping shapefile record into a dictionary"""

    def __init__(self, shp_reader) -> None:
        """
        initialize field mapper with shapefile Reader object
        :param shp_reader:
        """
        self.keys = [x[0] for x in shp_reader.fields[1:]]

    def make_record(self, shp_row: Union[ShapeRecord, Sequence]):
        """
        make record as a dictionary with keys coming from shapefile field names and values
        from given shapefile row
        :param shp_row: shapefile row object
        :return: dictionary field_name->record_value
        """
        if isinstance(shp_row, ShapeRecord):
            return dict(zip(self.keys, shp_row.record))
        else:
            return dict(zip(self.keys, shp_row))
