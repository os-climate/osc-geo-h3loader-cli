# Geospatial Capabilities

This product offers a geospatial temporal data mesh that uses
the H3 grid (created by Uber) to create a uniform mesh of the globe at
a variety of resolutions.

The geospatial components include:

- A server that serves location data
- a CLI that issues requests for location data

## Prerequisites

### Setting up your Environment

Some environment variables are used by various code and scripts.
Set up your environment as follows (note that "source" is used)

```bash
source ./bin/environment.sh
```

It is recommended that a Python virtual environment be created.
Several convenience scripts are available to create and activate
a virtual environment.

To create a new virtual environment run the below command
(it will create a directory called "venv" in your current working directory):

```bash
$PROJECT_DIR/bin/venv.sh
```

Once your virtual environment has been created, it can be activated
as follows (note: you _must_ activate the virtual environment
for it to be used, and the command requires `source` to ensure
environment variables to support venv are established correctly):

```bash
source $PROJECT_DIR/bin/vactivate.sh
```

Install the required libraries as follows:

```bash
pip install -r requirements.txt
```

## Shapefiles

Shapefiles are files that define a geographic region. They are used in this
example to ensure that processing only happens within a target region.
In order to run the below examples, shapefiles will need to be downloaded from
the following link:

Shapefiles source:

- [world-administrative-boundaries.zip](https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/world-administrative-boundaries/exports/shp?lang=en&timezone=America%2FNew_York):

Retrieved from parent site: <https://public.opendatasoft.com/explore/dataset/world-administrative-boundaries/export/>

- retrieved as a dataset from the "Geographic file formats" section,
  "Shapefile" element, by clicking the "Whole dataset" link

Create the `data/shapefiles/WORLD` directory as below
(if it does not already exist)

```bash
mkdir -p ./data/shapefiles/WORLD
```

Unzip the `world-administrative-boundaries.zip` file into the
`data/shapefiles/WORLD` directory. This should result in a
directory structure that looks like below:

```console
data
|-- shapefiles
    |-- WORLD
        |-- world-adminstrative-boundaries.prj
        |-- world-adminstrative-boundaries.cpg
        |-- world-adminstrative-boundaries.dbf
        |-- world-adminstrative-boundaries.shp
        |-- world-adminstrative-boundaries.shx
```

### Geospatial Data

The GISS temperature dataset contains data on global temperatures,
and is used as the raw data for the examples in this README.
It is used as sample data for some of the below examples.
It can be retrieved from the below links:

GISS Temperature:

- [v4.mean_GISS_homogenized.txt](https://data.giss.nasa.gov/gistemp/station_data_v4_globe/v4.mean_GISS_homogenized.txt.gz)
- [stations.txt](https://data.giss.nasa.gov/gistemp/station_data_v4_globe/station_list.txt)

These were retrieved from this parent site: <https://data.giss.nasa.gov/gistemp/station_data_v4_globe/>

Create the `data/geo_data/temperatures` directory using the
below command (if it does not already exist):

```bash
mkdir -p data/geo_data/temperatures
```

Copy both the `v4.mean_GISS_homogenized.txt` and `stations.txt` to the
`data/geo_data/temperatures` directory.

See [Data Loading](/docs/README-loading.md) for instructions on turning
this data into a geomesh dataset.

## Dataset types

There are two types of dataset supported by the geospatial server, and each
has slightly different interactions with endpoints.

The first type of dataset is a continuous or h3 dataset. This is a dataset
where data is interpolated between known values to generate a distribution with
values on hexes that do not contain data points themselves, but that
have data points nearby them. This can be useful for information like
temperature data, where the underlying distribution varies continuously,
and nearby data can be used to predict intermediate values without large errors.

The second type of dataset is a point dataset. This is a dataset where
data is stored as a raw collection of points, without interpolation. This
can be useful for datasets like asset locations, where data does not vary
continuously between points, and knowing nearby points cannot be used to
predict values as unknown points.

### Visualize Dataset

The `visualize-dataset` command allows a visual display of a numerical dataset
to be displayed on a map. It will generate an output html file that can
be viewed to see the visualization.
Colour scale will vary linearly between the
max and min value in the dataset, with the maximum color value
set in the max-color argument.

A settable threshold exists, and the visualization will not draw parts
of the grid that fall below a threshold value. Threshold is
calculated as min + ((max - min) \* threshold),
and any values below this will not be displayed.
Setting a threshold allows for faster generation of visualization, especially
when there are large chunks of data with minimum or near-minimum values that
do not meaningfully affect the information the visualization is trying to
convey.

```bash
DATABASE_DIR="./tmp" ;
DATASET="flood_data" ;
RESOLUTION=6 ;
VALUE_COLUMN="value" ;
RED=0 ;
GREEN=0 ;
BLUE=255 ;
OUTPUT_FILE="./tmp/visualize_flood_germany_6_10%_threshold_map_bounds.html" ;
MIN_LAT=46.5 ;
MAX_LAT=55.5 ;
MIN_LONG=4.5 ;
MAX_LONG=16.5 ;
THRESHOLD=0.1 ;

python ./src/cli/cli_visualize.py $VERBOSE visualize-dataset \
--database-dir $DATABASE_DIR \
--dataset $DATASET \
--resolution $RESOLUTION \
--value-column $VALUE_COLUMN \
--max-color $RED $GREEN $BLUE \
--output-file $OUTPUT_FILE \
--min-lat $MIN_LAT \
--max-lat $MAX_LAT \
--min-long $MIN_LONG \
--max-long $MAX_LONG \
--threshold $THRESHOLD
```

#### Visualizing point datasets

In order to visualize point datasets, the `ds-type` parameter will need
to be supplied, and set to "point". This will calculate a visualization by
taking the mean value of all points that fall within an h3 cell, at the
appropriate resolution.

```bash
DATABASE_DIR="./tmp" ;
DATASET="flood_data" ;
RESOLUTION=6 ;
VALUE_COLUMN="value" ;
RED=0 ;
GREEN=0 ;
BLUE=255 ;
OUTPUT_FILE="./tmp/visualize_flood_germany_6_10%_threshold_map_bounds.html" ;
MIN_LAT=46.5 ;
MAX_LAT=55.5 ;
MIN_LONG=4.5 ;
MAX_LONG=16.5 ;
THRESHOLD=0.1 ;
DS_TYPE="point" ;

python ./src/cli/cli_visualize.py $VERBOSE --host $HOST --port $PORT visualize-dataset \
--database-dir $DATABASE_DIR \
--dataset $DATASET \
--resolution $RESOLUTION \
--value-column $VALUE_COLUMN \
--max-color $RED $GREEN $BLUE \
--output-file $OUTPUT_FILE \
--min-lat $MIN_LAT \
--max-lat $MAX_LAT \
--min-long $MIN_LONG \
--max-long $MAX_LONG \
--threshold $THRESHOLD \
--ds-type $DS_TYPE
```

### Add Dataset to Metadata

In order to retrieve information from a dataset, that dataset's metadata
must be created. Use the `addmeta` command to add this metadata.

```bash
DATABASE_DIR="./tmp" ;
DATASET_NAME="giss_temperature" ;
DESCRIPTION="Temperature data for the entire globe" ;
VALUE_COLUMNS="{\"temperature\":\"REAL\"}" ;
KEY_COLUMNS="{\"h3_cell\":\"VARCHAR\"}" ;
DATASET_TYPE="h3" ;
python ./src/cli/cli_metadata.py $VERBOSE --host $HOST --port $PORT addmeta \
    --database_dir $DATABASE_DIR \
    --dataset_name $DATASET_NAME \
    --description "$DESCRIPTION" \
    --value_columns $VALUE_COLUMNS \
    --key_columns $KEY_COLUMNS \
    --dataset_type $DATASET_TYPE
```

### Show Dataset Metadata

The `showmeta` command retrieves all metadata currently available about
all datasets.

```bash
DATABASE_DIR="./tmp" ;
python ./src/cli/cli_metadata.py $VERBOSE --host $HOST --port $PORT showmeta \
    --database_dir $DATABASE_DIR
```
