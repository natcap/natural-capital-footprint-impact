# natural capital footprint impact
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Company footprint impact workflow (eventually to be made public)

This command-line script calculates metrics of the impact of human-made structures on certain ecosystem services, based on their physical footprint on the landscape.

Some useful definitions:
- **Asset**: A unit of physical infrastructure that occupies space on the surface of the earth, such as an office, restaurant, cell tower, hospital, pipeline, or billboard.
- **Footprint**: The area on the earth surface taken up by an asset.

Asset location data is usually available as point coordinates (latitude/longitude). The real footprint of an asset may be available, but usually is not. To account for differences in data availability, this script can be used in three different ways:
1. **Point mode**: Assets are provided by the user as latitude/longitude points. The actual asset footprint is not known or modeled. Ecosystem service statistics are calculated under each point only.
2. **Buffer mode**: Assets are provided by the user as latitude/longitude points. The asset footprint is modeled by creating a circular buffer with defined area around each point. Ecosystem service statistics are calculated under each buffer/footprint.
3. **Polygon mode**: Assets are provided by the user as footprint polygons. This mode is preferred if actual asset footprint data are available. Ecosystem service statistics are calculated under each footprint.

## Data you must provide

### asset vector

The instructions below assume that you have the following information about each asset of interest:
- its coordinate (latitude/longitude) point location
- its category
- its owner

The script requires that asset data is provided in a GDAL-supported vector format (such as GeoPackage). 

#### Point asset vector

Required for both **Point mode** and **Buffer mode**. Point data must be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All points must be in the first layer. All features in the layer must be of the `Point` type. `MultiPoint`s are not allowed. Any attributes that there in the original vector attribute table will be preserved in the output.

The asset vector layer contains an attribute table, where each row represents an asset. The following fields are used by the script:

1. Coordinate locations of each asset are in the `latitude` and `longitude` columns. These fields are required when using both **Point mode** and **Buffer mode**.
2. The `category` column determines footprint size. This field is required when using **Buffer mode** only. 

Footprint sizes vary widely, but correlate with the type of asset (for example, power plants take up more space than restaurants). We categorize assets using the S&P "facility category" designations. Other attributes, like the name of the ultimate parent company, may be used to aggregate data. {??? Add more information about what aggregation means and how it works. ???}

| latitude | longitude | category          | ultimate_parent_name    |
|----------|-----------|-------------------|-------------------------|
| 81.07    | 33.55     | Bank Branch       | XYZ Corp                |
| ...      | ...       | ...               | ...                     |

*Table 1. Asset vector attribute table field requirements for Point mode and Buffer mode.*


#### Polygon asset vector

Required for **Polygon mode**. Polygon data must be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All polygons must be in the first layer. All features in the layer must be of the `Polygon` or `MultiPolygon` type. Any attributes that there in the original vector attribute table will be preserved in the output.

If you are running the script in **Polygon mode**, no additional fields are required by the script. {??? Is this true ???}

## Data provided for you

### footprint data by asset category
CSV (comma-separated value) table, where each row represents an asset category.
The first column is named `category`. The category values will be cross-referenced with the *category* field in the asset table (Table 1).
The second column is named `area`. This is the size (in square meters) of footprint to draw for assets of this category. Footprints will be drawn as a circular buffer around each asset point.

| category          | area           |
|-------------------|----------------|
| Bank Branch       | 549.7          |
| ...               | ...            |

*Table 2. Buffer table: footprint area modeled for each asset category, used in Buffer mode.*

The provided footprint areas were derived by manually estimating the footprint area of real assets on satellite imagery. We took the median of a small sample from each category. You may modify or replace this table if you wish to use different data, but it must be in CSV format.

### ecosystem service data
CSV (comma-separated value) table, where each row represents an ecosystem service.
Columns are:
- `es_id`: A text (string) identifier for the ecosystem service
- `es_value_path`: File path to a geospatial raster map of the ecosystem service {??? File type requirements ???}
- `flag_threshold`: Flagging threshold value for the ecosystem service. Pixels with an ecosystem service value greater than this threshold will be flagged. {??? is this a number? how is it determined? Need to explain flags in more detail. ???}

| es_id    | es_value_path         | flag_threshold         |
|----------|-----------------------|------------------------|
| sediment | gs://foo-sediment.tif | 123                    |
| ...      | ...                   | ...                    |

*Table 3. Ecosystem service table: defines the ecosystem service layers that will be used by the script.*

You may modify or replace this table if you wish to use different ecosystem service data, but it must be in CSV format.

## Installation

1. [Install conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html), if you haven't already. We recommend using `conda` because it is the easiest way to install the `gdal` dependency. 
2. Run the following commands in the terminal:
    ```
    $ conda create -n footprint python gdal
    $ conda activate footprint
    $ pip install git+https://github.com/natcap/natural-capital-footprint-impact.git@main
    ```
3. The command `natural-capital-footprint-impact` should now be available:
   ```
   $ natural-capital-footprint-impact --help
   usage: ...
   ```

## Workflow
1. If your asset point data is in CSV format, convert it to a GDAL-supported vector format such as GeoPackage (GPKG):
```
ogr2ogr -s_srs EPSG:4326 -t_srs EPSG:4326 -oo X_POSSIBLE_NAMES=longitude -oo Y_POSSIBLE_NAMES=latitude assets.gpkg assets.csv
```
To do this in QGIS, use the *Add Delimited Text Layer* tool to add the CSV data as a point layer, then *Export > Save Features As* to save the layer to a GeoPackage.

In ArcGIS Pro, import the CSV data to a point layer using the *XY Data to Point* tool. This will create a point shapefile that you can use instead of a GeoPackage. 

2. If your asset data is in a geographic (non-projected) coordinate system (where distances are given in degrees), reproject it to a projected coordinate system (where distances are in meters), such as Eckert IV:
```
ogr2ogr -t_srs ESRI:54012 assets_eckert.gpkg assets.gpkg
```
This can also be done in QGIS with the Warp tool, and ArcGIS using the Project tool. Other projected coordinate systems may be used, such as UTM, as long as they are supported by GDAL (??? Emily, is this correct ???)

3. Run the workflow:
```
natural-capital-footprint-impact -e ECOSYSTEM_SERVICE_TABLE {points,polygons} [-b BUFFER_TABLE] asset_vector
```

## Modes of operation

{??? Add file naming requirements for footprint_results_path and company_results_path. Also provide an example for each mode. ???}

```
usage: natural-capital-footprint-impact [-h] -e ECOSYSTEM_SERVICE_TABLE [-b BUFFER_TABLE]
                                        {points,polygons} asset_vector footprint_results_path company_results_path

positional arguments:
  {points,polygons}     mode of operation. in points mode, the asset vector contains point geometries. in polygons mode, it contains polygon geometries.
  asset_vector          path to the asset vector
  footprint_results_path
                        path to write out the asset results vector
  company_results_path  path to write out the aggregated results table

options:
  -h, --help            show this help message and exit
  -e ECOSYSTEM_SERVICE_TABLE, --ecosystem-service-table ECOSYSTEM_SERVICE_TABLE
                        path to the ecosystem service table 
  -b BUFFER_TABLE, --buffer-table BUFFER_TABLE
                        buffer asset points according to values in this table 
```


### Point mode
`natural-capital-footprint-impact -e <ecosystem service table path> points <asset point vector path> <output vector path> <output table path>`

In **Point mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is not known or modeled. Statistics are calculated under each point only.

### Buffer mode
`natural-capital-footprint-impact -e <ecosystem service table path> points --buffer-table <buffer table path> <asset point vector path> <output vector path> <output table path>`

In **Buffer mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is modeled by buffering each point to a distance determined by the asset category in the Buffer table. Statistics are calculated under each footprint.

### Polygon mode
`natural-capital-footprint-impact -e <ecosystem service table path> polygons <asset polygon vector path> <output vector path> <output table path>`

In **Polygon mode**, you provide the assets as footprint polygons. This mode is preferred if asset footprint data is available. Statistics are calculated under each footprint.


## Input formats



## Output formats

{??? Add details about the output fields - names, units, description, etc. An example for each would be good too. ???}

The ecosystem services provided are:
- `coastal_risk_reduction_service`
- `nitrogen_retention_service`
- `sediment_retention_service`
- `nature_access`
- `endemic_biodiversity`
- `redlist_species`
- `species_richness`
- `kba`

### CSV and point vector
**Point mode** produces a CSV and a point vector in geopackage (.gpkg) format. Both contain the same data. These are copies of the input data with additional columns added. There is one column added for each ecosystem service. This column contains the ecosystem service value at each point, or `NULL` if there is no data available at that location.

### polygon vector
**Buffer mode** and **Polygon mode** both produce a polygon vector in geopackage (.gpkg) format. It is a copy of the input vector with additional columns added to the attribute table. There is one column added for each combination of ecosystem service and statistic.


