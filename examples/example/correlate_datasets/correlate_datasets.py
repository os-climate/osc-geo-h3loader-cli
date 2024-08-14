import argparse
import re
from typing import List, Optional, Tuple, Any, Dict

import duckdb
import pandas
from pandas import DataFrame

# Add the source to sys.path (this is a short-term fix)
import os
import sys

from pydantic import BaseModel, Field

from geoserver import metadata
from geoserver.geomesh import Geomesh
from shape import shape

current_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '../../..', 'src'))
print(parent_dir)
sys.path.append(parent_dir)


class PointDataRow(BaseModel):
    latitude: float = Field(
        description="The latitude of the point this data row represents")

    longitude: float = Field(
        description="The longitude of the point this data row represents")

    values: Dict[str, Any] = Field(
        description="Any data values associated with this row's cell."
                    " Keys represent the column the data element comes from,"
                    " with the value being what was present in that column.")

    cells: Dict[str, str] = Field(
        description="The cells this point is contained within,"
                    " at various resolutions")


def load_dataset(
        ds_name: str,
        db_dir: str,
        shapefile: str,
        region: str
) -> DataFrame:
    # the particular dataset that is being used here will be a point dataset
    dataset = shapefile_get_point(
        db_dir,
        ds_name, shapefile, region,
        None, None, None
    )
    ds = point_row_to_df(dataset)
    print(f"retrieved {len(ds)} rows")
    return ds


def shapefile_get_point(
        geo_out_db_dir: str,
        dataset_name: str,
        shapefile: str,
        region: Optional[str],
        year: Optional[int],
        month: Optional[int],
        day: Optional[int]
) -> List[PointDataRow]:
    metadb = metadata.MetadataDB(geo_out_db_dir)

    if not metadb.ds_meta_exists(dataset_name):
        raise Exception(f"dataset {dataset_name} not registered"
                        f" in metadata.")

    meta = metadb.get_ds_metadata(dataset_name)
    val_col_names: List[str] = meta["value_columns"]["key"]
    ds_type = meta["dataset_type"]

    table_name = table_name_from_ds_type(
        dataset_name, ds_type
    )

    # TODO: figure out how to determine buffer resolution here
    #  as for the moment I just set a default and moved on
    buffer = Geomesh.get_buffer(3)

    shp = shape.Shape(shapefile)

    if not os.path.exists(geo_out_db_dir):
        raise ValueError(
            "db dir: {self.geo_out_db_dir} does not exist")

    if not metadb.ds_meta_exists(dataset_name):
        raise ValueError(
            f"dataset {dataset_name} not registered in metadata.")

    out_db_path = os.path.join(geo_out_db_dir, f"{dataset_name}.duckdb")
    connection = duckdb.connect(database=out_db_path)

    k_cols = meta["key_columns"]["key"]
    if "day" in k_cols:
        interval = "daily"
    elif "month" in k_cols:
        interval = "monthly"
    elif "year" in k_cols:
        interval = "yearly"
    else:
        interval = "one_time"

    time_filter, time_params = get_time_filters(
        interval, year, month, day)

    # get maximum lat/long for a given shapefile region to get the database
    #  to filter out as many datapoints as possible before we have to
    #  perform the more expensive checks on exact inclusion
    (min_long, min_lat, max_long, max_lat) = shp.get_max_lat_long(region)

    lat_long_filter = f"""
        latitude BETWEEN {min_lat} AND {max_lat}
        AND
        longitude BETWEEN {min_long} AND {max_long}
    """

    full_where = combine_where_clauses([time_filter, lat_long_filter])
    value_columns = ", ".join(val_col_names)

    col_list = connection.execute(f"describe {table_name}").fetchall()
    all_col_names = list(map(
        lambda c: c[0],
        col_list
    ))
    cell_col_names = list(filter(
        lambda cn: re.match("res[0-9]*", cn) is not None,
        all_col_names
    ))
    cell_column = ", ".join(cell_col_names)

    sql = f"""
        SELECT {cell_column}, latitude, longitude, {value_columns}
        FROM {table_name}
        {full_where}
    """

    raw_result: List[Tuple] = connection \
        .execute(sql, time_params).fetchall()

    point_rows = row_to_point_out(
        raw_result, val_col_names, cell_col_names)

    filter(
        lambda row: shp.point_within_shape(
            row.latitude, row.longitude, region
        ),
        point_rows
    )

    return point_rows


def row_to_point_out(
        rows: List[Tuple],
        val_col_names: List[str],
        cell_col_names: List[str]
) -> List[PointDataRow]:
    out = []
    for row in rows:
        num_cell_cols = len(cell_col_names)
        cell_cols = {}
        values = {}

        for i in range(0, num_cell_cols):
            cell_cols[cell_col_names[i]] = row[i]

        for i in range(0, len(row) - (num_cell_cols + 2)):
            values[val_col_names[i]] = row[num_cell_cols + 2 + i]

        out.append(PointDataRow(
            latitude=row[num_cell_cols],
            longitude=row[num_cell_cols + 1],
            cells=cell_cols,
            values=values
        ))
    return out


def combine_where_clauses(clauses: List[Optional[str]]) -> str:
    joined = " AND ".join(
        filter(
            lambda x: x is not None,
            clauses
        )
    )
    return f"WHERE {joined}"


def table_name_from_ds_type(
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


def get_time_filters(
        interval: str,
        year: Optional[int],
        month: Optional[int],
        day: Optional[int],

) -> Tuple[Optional[str], List[Any]]:
    valid_intervals = ["yearly", "monthly", "daily", "one_time"]
    if interval not in valid_intervals:
        raise ValueError(
            f"received invalid interval: {interval}. Valid intervals"
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


def point_row_to_df(rows: List[PointDataRow]) -> DataFrame:
    lst = []
    for row in rows:
        d = {
            'latitude': row.latitude,
            'longitude': row.longitude
        }
        for val_col_name in row.values.keys():
            d[val_col_name] = row.values[val_col_name]
        for cell_col_name in row.cells.keys():
            d[cell_col_name] = row.cells[cell_col_name]
        lst.append(d)

    df = pandas.DataFrame.from_records(lst)
    return df


def average_by_cell(flood_data: DataFrame, res: int) -> DataFrame:
    cell_col = f"res{res}"
    val_col = "value"
    only_relevant_cols = flood_data[[cell_col, val_col]]
    return only_relevant_cols \
        .groupby([f'res{res}']) \
        .mean() \
        .reset_index()


def correlate_anonymized(
        flood: DataFrame, asset: DataFrame, res: int
) -> DataFrame:
    cell_col = f'res{res}'
    all_result = asset \
        .set_index(cell_col) \
        .join(flood.set_index(cell_col))

    return all_result[['value', 'uuid']]


def load_non_anonymized(parquet_location: str) -> DataFrame:
    return pandas.read_parquet(parquet_location)


def deanon_flood(uuid_flood: DataFrame, non_anon: DataFrame) -> DataFrame:
    return uuid_flood.set_index('uuid').join(non_anon.set_index('uuid'))


def get_arg_parser():
    parser = argparse.ArgumentParser(description="asset to flood correlation")

    parser.add_argument(
        "--flood-dataset",
        required=True,
        help="the dataset containing flood data"

    )
    parser.add_argument(
        "--asset-dataset",
        required=True,
        help="the dataset containing asset data"
    )
    parser.add_argument(
        "--non-anon-file",
        required=True,
        help="the parquet file holding the non-anonymized data"
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="where output will be placed"
    )
    parser.add_argument(
        "--db-dir",
        required=True,
        help="Where the geomesh server stores databases"
    )
    parser.add_argument(
        "--shapefile",
        required=True,
        help="Shapefile that defines region data is to be retrieved for"
    )
    parser.add_argument(
        "--region",
        required=True,
        help="region within shapefile that defines where data is to be "
             "retrieved for"
    )
    parser.add_argument(
        "--resolution",
        required=True,
        type=int,
        help="The resolution of h3 cells to use when correlating data"
    )

    return parser


if __name__ == "__main__":
    args = get_arg_parser().parse_args()

    shapefile = args.shapefile
    region = args.region
    db_dir = args.db_dir
    res = args.resolution
    non_anon_file = args.non_anon_file
    out_path = args.output_path

    pandas.set_option('display.max_columns', None)
    pandas.set_option('display.width', None)

    print("Loading flood dataset")
    flood_data = load_dataset(args.flood_dataset, db_dir, shapefile, region)
    print("Loading asset dataset")
    asset_data = load_dataset(args.asset_dataset, db_dir, shapefile, region)
    print("Datasets loaded")

    print(f"Averaging flood data by cell as resolution {res}")
    flood_data_cell_avg = average_by_cell(flood_data, res)
    print("flood data averaged")

    print("Correlating anonymized (uuid-only) asset data with flood data")
    correlated_anon = correlate_anonymized(flood_data_cell_avg, asset_data, res)
    print("flood data correlated with anonymized asset data")

    with_flood_values = correlated_anon[correlated_anon['value'].notna()] \
        .reset_index()
    with_flood_values = with_flood_values.rename(
        columns={"value": "flood_depth", "res9": "cell_id"})
    num_with_values = len(with_flood_values)
    num_total = len(correlated_anon)

    print(f"when correlated {num_with_values}/{num_total}"
          f" assets had non-zero flood depth.")

    print("\nshowing 5 example rows from correlated anonymized data:")

    print(with_flood_values.head(5))

    print("\nThe following steps require access to the non-anonymized data,"
          " and in production would be performed at the client site, rather"
          " than on the geo server itself. ")
    print("Loading non-anonymized data.")
    non_anon_assets = load_non_anonymized(non_anon_file)
    print("Adding additional fields from de-anonymized data to output")
    deanon = deanon_flood(correlated_anon, non_anon_assets)
    deanon = deanon.rename(columns={"value": "flood_depth"}).reset_index()

    print("\nshowing 5 example rows from de-anonymized data")

    print(deanon[deanon['flood_depth'].notna()].head(5))

    print("correlated data combined with non-anonymized data")

    deanon.to_parquet(out_path)

    print(f"wrote output to {out_path}")

    print("done")
