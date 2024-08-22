# Copyright 2024 Broda Group Software Inc.
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
#
# Created: 2024-08-19 by davis.broda@brodagroupsoftware.com
import json
import logging
import os.path
from typing import List, Optional, Dict, Any, Tuple

import pandas

from geoserver.geomesh import Geomesh
import visualizer


# Set up logging
LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)


# Abstract class
class CliExecVisualize:

    def __init__(self):
        pass

    def visualize_dataset(
            self,
            database_dir: str,
            resolution: int,
            dataset: str,
            value_column: str,
            max_color_rgb: Tuple[int, int, int],  # hex rgb values
            output_file: str,
            min_lat: float,
            max_lat: float,
            min_long: float,
            max_long: float,
            threshold: Optional[float],
            year: Optional[int],
            month: Optional[int],
            day: Optional[int],
            ds_type: str,
            visualizer_type: str = "HexGridVisualizer"
    ):
        geo = Geomesh(database_dir)
        ds = geo.bounding_box_get(
            dataset,
            resolution,
            min_lat,
            max_lat,
            min_long,
            max_long,
            year,
            month,
            day
        )
        ds_pandas = pandas.json_normalize(ds)

        if visualizer_type == "HexGridVisualizer":
            vis = visualizer.HexGridVisualizer(
                ds_pandas,
                value_column,
                max_color_rgb,
                min_lat,
                max_lat,
                min_long,
                max_long
            )
            vis.visualize_dataset(resolution, output_file, threshold, ds_type)

        elif visualizer_type == "PointLocationVisualizer":
            if ds_type != "point":
                raise ValueError(
                    "PointLocationVisualizer visualizer type is not compatible"
                    f" with dataset type {ds_type}"
                )
            vis = visualizer.PointLocationVisualizer(
                ds_pandas,
                value_column,
                min_lat,
                max_lat,
                min_long,
                max_long
            )
            vis.visualize_dataset(output_file)

        print(f"created visualization file at location: {output_file}")
