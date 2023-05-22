# natural capital footprint impact
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Company footprint impact workflow (eventually to be made public)

This script calculates metrics of the impact of man-made structures on certain ecosystem services, based on their physical footprint on the landscape.

- Asset: A unit of physical infrastructure that occupies space on the surface of the earth, such as an office, a restaurant, a cell tower, a hospital, a pipeline, or a billboard.
- Footprint: The area on the earth surface taken up by an asset.

Asset location data is usually available as point coordinates. The real footprint of an asset is usually not available. We approximate the footprint by drawing a circle around the point. If actual footprint data is available, you may substitute that in.
Footprint sizes vary widely, but correlate with the type of asset (for example, power plants take up more space than restaurants). We categorize assets using the S&P "facility category" designations.

## Data you must provide
The instructions below assume that you begin with the following information about the assets of interest:
- its coordinate point location
- its facility category
- its owner

This data should be formatted into a table where each row represents an asset.
Coordinate locations of each asset are in the `latitude` and `longitude` columns.
The `facility_category` column determines footprint size. Other attributes, like the name of the ultimate parent company, may be used to aggregate data.

| latitude | longitude | facility_category | ultimate_parent_name    |
|----------|-----------|-------------------|-------------------------|
| 81.07    | 33.55     | Bank Branch       | XYZ Corp                |
| ...      | ...       | ...               | ...                     |

## Data provided for you

### footprint data by asset category
A table where each row represents an asset category.
The first column is named after the asset category attribute. In this example, `facility_category` is used consistent with the S&P asset data.
The second column is named `area`. This is the size (in square meters) of footprint to draw for assets of this category.

| facility_category | footprint_area |
|-------------------|----------------|
| Bank Branch       | 549.7          |
| ...               | ...            |

This data was derived by manually estimating the footprint area of real assets on satellite imagery. We took the median of a small sample from each category. You may modify or replace this table if you wish to use different data.

### ecosystem service data
Each row represents an ecosystem service.
Columns are:
- `es_id`: An identifier for the ecosystem service
- `path`: Path to a global raster map of the ecosystem service
- 0 - 100: Percentile values of the ecosystem service globally

| es_id    | path                  | 0   | 1     | 2    | ... | 100    |
|----------|-----------------------|-----|-------|------|-----|--------|
| sediment | gs://foo-sediment.tif | 0   | 0.003 | 1.45 | ... | 2089.9 |
| ...      | ...                   | ... | ...   | ...  | ... | ...    |

The percentiles are pre-calculated and stored in this table because they are time-consuming to calculate.
You may modify or replace this table if you wish to use different data.

## Workflow
1. If your point data is in CSV format, convert it to a GDAL-supported vector format such as GPKG:
```
ogr2ogr -s_srs EPSG:4326 -t_srs EPSG:4326 -oo X_POSSIBLE_NAMES=longitude -oo Y_POSSIBLE_NAMES=latitude assets.gpkg assets.csv
```

2. If your point data is in a geographic (non-projected) coordinate system, such as latitude/longitude, reproject it to a projected coordinate system, such as Eckert IV:
```
ogr2ogr -t_srs ESRI:54012 assets_eckert.gpkg assets.gpkg
```

3. Run the workflow:
```
python src/workflow.py assets_eckert.gpkg out.csv
```

## Modes of operation

### mode 1
In mode 1, structures are modeled as coordinate points. The actual footprint area is not known or assumed.

### mode 2
In mode 2, structures are modeled as coordinate points. The actual footprint area is not known, but is approximated by drawing a circle around each point.

### mode 3
In mode 3, the actual footprints are known. Structures are modeled as polygons outlining their footprint on the landscape.

## Summary of modes

| mode | command                                             | input format   | output format                 |
|------|-----------------------------------------------------|----------------|-------------------------------|
| 1    | `python footprint_impact.py points <path>`          | point vector   | CSV and point vector (GPKG)   |
| 2    | `python footprint_impact.py points --buffer <path>` | point vector   | CSV and polygon vector (GPKG) |
| 3    | `python footprint_impact.py polygons <path>`        | polygon vector | CSV and polygon vector (GPKG) |

## Input formats

### point vector
Point data may be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All points must be in the first layer. All features in the layer must be of the `Point` type. `MultiPoint`s are not allowed. No attributes are required. Any attributes that there are will be preserved in the output.

### polygon vector
Polygon data may be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All polygons must be in the first layer. All features in the layer must be of the `Polygon` or `MultiPolygon` type. Any attributes that there are will be preserved in the output.

## Output formats

The ecosystem services are:
- `sediment`

### CSV and point vector
Mode 1 produces a CSV and a point vector in geopackage (.gpkg) format. Both contain the same data. These are copies of the input data with additional columns added. There is one column added for each ecosystem service. This column contains the ecosystem service value at each point, or `NULL` if there is no data available at that location.

### polygon vector
Modes 2 and 3 produce a polygon vector in geopackage (.gpkg) format. It is a copy of the input vector with additional columns added to the attribute table. There is one column added for each combination of ecosystem service and statistic.

The statistics are:
- `min`: minimum ecosystem service value found in pixels underneath the footprint polygon
- `max`: maximum ecosystem service value found in pixels underneath the footprint polygon
- `sum`: sum of ecosystem service pixel values underneath the footprint polygon
- `count`: number of pixels with data underneath the footprint polygon
- `nodata_count`: number of pixels without data underneath the footprint polygon



