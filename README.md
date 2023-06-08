# natural capital footprint impact
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Company footprint impact workflow (eventually to be made public)

This script calculates metrics of the impact of human-made structures on certain ecosystem services, based on their physical footprint on the landscape.

Some useful definitions:
- **Asset**: A unit of physical infrastructure that occupies space on the surface of the earth, such as an office, a restaurant, a cell tower, a hospital, a pipeline, or a billboard.
- **Footprint**: The area on the earth surface taken up by an asset.

Asset location data is usually available as point coordinates (latitude/longitude). The real footprint of an asset may be available, but usually is not. To account for differences in data availability, this tool can be used in three different ways:
1. **Point mode**: Assets are provided by the user as latitude/longitude points. The actual asset footprint is not known or modeled. Ecosystem service statistics are calculated under each point only.
2. **Buffer mode**: Assets are provided by the user as latitude/longitude points. The asset footprint is estimated by buffering (drawing a circle around) each point to a distance determined by the asset category. Ecosystem service statistics are calculated under each buffer/footprint.
3. **Polygon mode**: Assets are provided by the user as footprint polygons. This mode is preferred if actual asset footprint data are available. Ecosystem service statistics are calculated under each footprint.

## Data you must provide

### asset location data

The instructions below assume that you have the following information about each asset of interest:
- its coordinate point location
- its category
- its owner

The tool requires that asset data is provided in a GDAL-supported vector format (such as GeoPackage). The vector layer contains an attribute table, where each row represents an asset. The following fields are used by the tool:

1. Coordinate locations of each asset are in the `latitude` and `longitude` columns. This field is required when using both **Point mode** and **Buffer mode**.
2. The `category` column determines footprint size. This field is required when using **Buffer mode** only. 

Footprint sizes vary widely, but correlate with the type of asset (for example, power plants take up more space than restaurants). We categorize assets using the S&P "facility category" designations. Other attributes, like the name of the ultimate parent company, may be used to aggregate data.

| latitude | longitude | facility_category | ultimate_parent_name    |
|----------|-----------|-------------------|-------------------------|
| 81.07    | 33.55     | Bank Branch       | XYZ Corp                |
| ...      | ...       | ...               | ...                     |

Table 1. User-provided asset data attibute table field requirements.

## Data provided for you

### footprint data by asset category
CSV (comma-separated value) table, where each row represents an asset category.
The first column is named `category`. The category values will be cross-referenced with the categories in the asset table.
The second column is named `area`. This is the size (in square meters) of footprint to draw for assets of this category. Footprints will be drawn as a circular buffer around each asset point.

| category          | area           |
|-------------------|----------------|
| Bank Branch       | 549.7          |
| ...               | ...            |

Table 2. Script-provided facility category table, used for buffering point locations for different category types.

This data was derived by manually estimating the footprint area of real assets on satellite imagery. We took the median of a small sample from each category. You may modify or replace this table if you wish to use different data.

### ecosystem service data
CSV (comma-separated value) table, where each row represents an ecosystem service.
Columns are:
- `es_id`: A text (string) identifier for the ecosystem service
- `es_value_path`: Path to a geospatial raster map of the ecosystem service
- `flag_threshold`: Flagging threshold value for the ecosystem service. Pixels with an ecosystem service value greater than this threshold will be flagged.

| es_id    | es_value_path         | flag_threshold         |
|----------|-----------------------|------------------------|
| sediment | gs://foo-sediment.tif | 123                    |
| ...      | ...                   | ...                    |

Table 3. Table defining the ecosystem service layers that will be used by the script.

You may modify or replace this table if you wish to use different ecosystem service data, but it must be in CSV format.

## Installation

```
git clone https://github.com/natcap/natural-capital-footprint-impact.git
conda create -n footprint python gdal
conda activate footprint
pip install .
```
The command `natural-capital-footprint-impact` should now be available.

## Workflow
1. If your asset point data is in CSV format, convert it to a GDAL-supported vector format such as GPKG:
```
ogr2ogr -s_srs EPSG:4326 -t_srs EPSG:4326 -oo X_POSSIBLE_NAMES=longitude -oo Y_POSSIBLE_NAMES=latitude assets.gpkg assets.csv
```
To do this in QGIS, use the *Add Delimited Text Layer* tool to add the CSV data as a point layer, then *Export > Save Features As* to save the layer to a GeoPackage.

In ArcGIS Pro, import the CSV data to a point layer using the *XY Data to Point* tool. This will create a point shapefile that you can use instead of a GeoPackage. 

2. If your asset data is in a geographic (non-projected) coordinate system, such as latitude/longitude, reproject it to a projected coordinate system, such as Eckert IV:
```
ogr2ogr -t_srs ESRI:54012 assets_eckert.gpkg assets.gpkg
```
This can also be done in QGIS with the Warp tool, and ArcGIS using the Project tool. Other projected coordinate systems may be used, such as UTM, as long as they are supported by GDAL (?? Emily, is this correct?)

3. Run the workflow:
```
natural-capital-footprint-impact -e ECOSYSTEM_SERVICE_TABLE {points,polygons} [--buffer-table BUFFER_TABLE] asset_vector
```

## Modes of operation

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
                        buffer points according to values in this table
```


### Point mode
`natural-capital-footprint-impact -e <ecosystem service table path> points <asset point vector path> <output vector path> <output table path>`

In **Point mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is not known or modeled. Statistics are calculated under each point only.

### Buffer mode
`natural-capital-footprint-impact -e <ecosystem service table path> points --buffer-table <buffer table path> <asset point vector path> <output vector path> <output table path>`

In **Buffer mode**, you provide the assets as coordinate points. The asset footprint is modeled by buffering each point to a distance determined by the asset category. Statistics are calculated under each footprint.

### Polygon mode
`natural-capital-footprint-impact -e <ecosystem service table path> polygons <asset polygon vector path> <output vector path> <output table path>`

In **Polygon mode**, you provide the assets as footprint polygons. This mode is preferred if asset footprint data is available. Statistics are calculated under each footprint.


## Input formats

### point vector
Point data may be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All points must be in the first layer. All features in the layer must be of the `Point` type. `MultiPoint`s are not allowed. No attributes are required. Any attributes that there are will be preserved in the output.

### polygon vector
Polygon data may be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All polygons must be in the first layer. All features in the layer must be of the `Polygon` or `MultiPolygon` type. Any attributes that there are will be preserved in the output.

## Output formats

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

{SW: Need to describe this attribute table}

