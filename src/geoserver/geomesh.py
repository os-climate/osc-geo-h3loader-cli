# Copyright 2023 Broda Group Software Inc.
#
# Created: 2023-10-16 by eric.broda@brodagroupsoftware.com

import logging
import math
import os
from math import sqrt
from typing import Tuple, List, Any, Dict, Optional, Set

import duckdb
import h3
from pydantic import BaseModel, Field
from shapely.geometry import Polygon

import re

from geoserver import metadata
from common import dataset_utilities, const
from cli import visualizer
from shape import shape

# Set up logging
LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)

VALID_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
                "OCT", "NOV", "DEC"]
INT_TO_MONTH = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AUG",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC"
}

NUM_NEIGHBOURS = 3
KM_PER_DEGREE = 110  # Each degree is about 110 KM

MIN_LAT, MAX_LAT = -60.0, 85.0  # Excluding Antarctica
MIN_LONG, MAX_LONG = -180.0, 180.0  # Full range of longitudes


class Geomesh:
    # Total number of cells at a given resolution
    CELLS_AT_RESOLUTION = [
        122,                # 0
        842,                # 1
        5882,               # 2
        41162,              # 3
        288122,             # 4
        2016842,            # 5
        14117882,           # 6
        98825162,           # 7
        691776122,          # 8
        4842432842,         # 9
        33897029882,        # 10
        237279209162,       # 11
        1660954464122,      # 12
        11626681248842,     # 13
        81386768741882,     # 14
        569707381193162     # 15
    ]

    # Average cell area in km2 at a given resolution
    CELLS_KM2_AT_RESOLUTION = [
        4357449.42,     # 0  (radius: 1,387,019,227,683m, or 1,387,019km)
        609788.44,      # 1  (radius:   194,101,689,503m)
        86801.78,       # 2  (radius:    27,629,864,839m)
        12393.43,       # 3  (radius:     3,944,952,774m)
        1770.35,        # 4  (radius:       563,519,160m)
        252.90,         # 5  (radius:        80,501,798m)
        36.129,         # 6  (radius:        11,500,237m)
        5.161293360,    # 7  (radius:         1,642,890m)
        0.737327598,    # 8  (radius:           234,698m)
        0.105332513,    # 9  (radius:            33,528m)
        0.015047502,    # 10 (radius:             4,789m)
        0.002149643,    # 11 (radius:               684m)
        0.000307092,    # 12 (radius:                97m)
        0.000043870,    # 13 (radius:                13m)
        0.000006267,    # 14 (radius:                 2m)
        0.000000895     # 15 (radius:               0.3m)
    ]

    def __init__(
            self,
            geo_out_db_dir: str | None
    ):
        """
        Initialize class

        :param geo_out_db_dir:
            The directory where databases containing processed data
            will be created
        :type geo_out_db_dir: str
        """

        self.geo_out_db_dir = geo_out_db_dir

        # some commands don't need database, so allow None in that case
        if geo_out_db_dir is not None:
            if not os.path.exists(self.geo_out_db_dir):
                logger.info(
                    f"database directory {self.geo_out_db_dir} did not"
                    f"exist. Creating this directory now.")
                os.makedirs(self.geo_out_db_dir)
            self.metadb = metadata.MetadataDB(self.geo_out_db_dir)


    def bounding_box_get(
            self,
            dataset_name: str,
            resolution: int,
            min_lat: float,
            max_lat: float,
            min_long: float,
            max_long: float,
            year: Optional[int],
            month: Optional[int],
            day: Optional[int]
    ) -> List[Dict[str, Any]]:
        if not self.metadb.ds_meta_exists(dataset_name):
            raise Exception(f"dataset {dataset_name} not registered"
                            f" in metadata.")

        meta = self.metadb.get_ds_metadata(dataset_name)
        col_names: List[str] = meta["value_columns"]["key"]
        ds_type = meta["dataset_type"]

        table_name = self._table_name_from_ds_type(
            dataset_name, ds_type, resolution
        )

        ds_db_path = self._get_db_path(dataset_name)
        connection = duckdb.connect(database=ds_db_path)

        col_names: List[str] = meta["value_columns"]["key"]
        value_columns = ", ".join(col_names)

        cells = list(self._get_h3_in_boundary(
            resolution,
            min_lat,
            max_lat,
            min_long,
            max_long,
        ))

        k_cols = meta["key_columns"]["key"]
        if "day" in k_cols:
            interval = "daily"
        elif "month" in k_cols:
            interval = "monthly"
        elif "year" in k_cols:
            interval = "yearly"
        else:
            interval = "one_time"

        time_filter, time_params = self._get_time_filters(
            interval, year, month, day)

        cells_per_part = 20000
        if len(cells) > cells_per_part:
            num_parts = math.ceil(float(len(cells)) / float(20000))

            cells_split = []
            for index in range(num_parts):
                cells_split.append(
                    cells[
                    index * cells_per_part:
                    cells_per_part * (index + 1)
                    ])
        else:
            cells_split = [list(cells)]

        data = []

        if ds_type == "h3":
            cell_column = const.CELL_COL
        elif ds_type == "point":
            cell_column = dataset_utilities.get_point_res_col(resolution)
        else:
            raise ValueError(
                "only h3 and point dataset types are supported"
                " for retrieving values within radius."
                f" Provided type was: {ds_type}"
            )

        for cell_part in cells_split:
            part_str = ""
            for cell in cell_part:
                part_str = part_str + f"'{cell}',"
            part_str = part_str[:-1]
            in_clause = f"""
                          {cell_column} IN ({part_str})
                       """

            full_where = self._combine_where_clauses([time_filter, in_clause])

            sql = f"""
                       SELECT {cell_column}, latitude, longitude, {value_columns}
                       FROM {table_name}
                       {full_where}
                   """

            res = connection.execute(sql, time_params).fetchall()

            for res_row in res:
                data.append(res_row)

        # format output as a json object
        out = []
        for row in data:
            num_val_cols = len(col_names)
            out_json = {
                const.CELL_COL: row[0],
                const.LATITUDE_COL: row[1],
                const.LONGITUDE_COL: row[2],
            }
            for i in range(0, num_val_cols):
                index = i + 3
                out_json[col_names[i]] = row[index]
            out.append(out_json)
        return out

    #####
    # INTERNAL
    #####

    def _get_h3_in_boundary(
            self,
            res: int,
            min_lat: float,
            max_lat: float,
            min_long: float,
            max_long: float,
    ) -> Set[str]:

        from shapely import Polygon
        from shapely.geometry import shape
        bot_left = (min_lat, min_long)
        top_left = (max_lat, min_long)
        top_right = (max_lat, max_long)
        bot_right = (min_lat, max_long)
        coords = (bot_left, top_left, top_right, bot_right, bot_left)
        boundary_poly = Polygon(coords)

        geojson = shape(boundary_poly).__geo_interface__
        overlap_cells = h3.polyfill(geojson, res)
        return set(overlap_cells)


    # TODO: have to replace this with more generic get_key_col_filters
    #   or something like that
    def _get_time_filters(
            self,
            interval: str,
            year: Optional[int],
            month: Optional[int],
            day: Optional[int],

    ) -> Tuple[Optional[str], List[Any]]:
        valid_intervals = ["yearly", "monthly", "daily", "one_time"]
        if interval not in valid_intervals:
            raise ValueError(
                f"recieved invalid interval: {interval}. Valid intervals"
                f" are {valid_intervals}"
            )

        has_year = ["yearly", "monthly", "daily"]

        f = None
        params = []
        if interval in has_year:
            if year is None:
                raise ValueError(
                    "No year was provided. Year must be provided for"
                    f" interval: {interval}"
                )
            else:
                params = [year]
                f = "year = ?"

        if interval == "monthly" or interval == "daily":
            if month is None:
                raise ValueError(
                    "No month was provided. Month must be provided for"
                    f" interval: {interval}"
                )
            else:
                f = f"{f} AND month = ?"
                params.append(month)

        if interval == "daily":
            if day is None:
                raise ValueError(
                    "No day was provided. Day must be provided for"
                    f" interval: {interval}"
                )
            else:
                f = f"{f} AND day = ?"
                params.append(day)

        return f, params

    def _table_name_from_ds_type(
            self,
            dataset_name: str,
            ds_type: str,
            resolution: Optional[int] = None
    ):
        if ds_type not in metadata.VALID_DATASET_TYPES:
            raise ValueError(
                f"dataset type: {ds_type} is not a valid type."
                f" Valid types: {metadata.VALID_DATASET_TYPES}"
            )

        if ds_type == "h3":
            if resolution is None:
                raise ValueError(
                    "resolution parameter cannot be None for h3 dataset"
                )
            table_name = dataset_name + f"_{resolution}"
        elif ds_type == "point":
            table_name = dataset_name
        else:
            raise ValueError(
                f"dataset type: {ds_type} not yet implemented"
            )
        return table_name

    def _combine_where_clauses(self, clauses: List[Optional[str]]) -> str:
        joined = " AND ".join(
            filter(
                lambda x: x is not None,
                clauses
            )
        )
        return f"WHERE {joined}"

    @staticmethod
    def get_buffer(resolution: int, multiplier: float = 1.5) -> float:

        cell_km2 = Geomesh.CELLS_KM2_AT_RESOLUTION[resolution]
        cell_radius_km = math.sqrt(cell_km2 / math.pi)

        buffer = 0
        if resolution >= 2:
            buffer = cell_radius_km / KM_PER_DEGREE * multiplier
        logger.info(f"buffer degrees:{buffer} km:{buffer * KM_PER_DEGREE}")

        return buffer

    def _get_db_path(self, db_name: str) -> str:
        return os.path.join(self.geo_out_db_dir, f"{db_name}.duckdb")