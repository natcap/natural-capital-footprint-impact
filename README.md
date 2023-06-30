# natural capital footprint impact
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Company footprint impact workflow (eventually to be made public)

This command-line script calculates metrics of the impact of human-made structures on certain ecosystem services, based on their physical footprint on the landscape.

The ecosystem services provided are:
- `coastal_risk_reduction_service`: Relative value of coastal and marine habitats for reducing the risk of erosion and inundation from storms for people who live near the coast. Risk reduction is calculated using the InVEST Coastal Vulnerability model. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. Values are unitless, representing a relative index of risk reduction times the number of people who benefit.
- `nitrogen_retention_service`: Nitrogen that is retained by the landscape, keeping it out of streams, times the number of people who live downstream who may benefit from cleaner water. Nitrogen retention is calculated using the InVEST Nutrient Delivery Ratio (NDR) model. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. Values are unitless, representing kilograms of nitrogen retained times number of people who benefit.
- `sediment_retention_service`: Sediment that is retained by the landscape, keeping it out of streams, times the number of people who live downstream who may benefit from cleaner water. Sediment retention is calculated using the InVEST Sediment Delivery Ratio (SDR) model. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. Values are unitless, representing tons of sediment retained times number of people who benefit.
- `nature_access`: The number of people within 1 hour travel distance of every pixel. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019.
- `kba_within_1km`: Value indicating whether each pixel is within 1 kilometer of a Key Biodiversity Area (KBA) or not. Adapted from data created for Damania et al. (2023). KBAs are from BirdLife International (2019). {??? Emily, are your values binary 0/1 or something else ???}

Some useful definitions:
- **Asset**: A unit of physical infrastructure that occupies space on the surface of the earth, such as a mine, office, restaurant, cell tower, hospital, pipeline, or billboard.
- **Footprint**: The area on the earth surface taken up by an asset.

Asset location data is usually available as point coordinates (latitude/longitude). The real footprint of an asset may be available, but usually is not. To account for differences in data availability, this script can be used in three different ways:
1. **Point mode**: Assets are provided by the user as latitude/longitude points. The actual asset footprint is not known or modeled. Ecosystem service statistics are calculated under each point only.
2. **Buffer mode**: Assets are provided by the user as latitude/longitude points. The asset footprint is modeled by creating a circular buffer with defined area around each point. Ecosystem service statistics are calculated under each buffer/footprint.
3. **Polygon mode**: Assets are provided by the user as footprint polygons. This mode is preferred if actual asset footprint data are available. Ecosystem service statistics are calculated under each footprint.

## Data you must provide

### asset vector

#### Point asset vector

Required for both **Point mode** and **Buffer mode**. Point data must be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All points must be in the first layer. All features in the layer must be of the `Point` type. `MultiPoint`s are not allowed. Any attributes that exist in the original vector attribute table will be preserved in the output.

The asset vector layer contains an attribute table, where each row represents an asset. The following fields are used by the script:

1. Coordinate locations of each asset are in the `latitude` and `longitude` columns. These fields are required when using both **Point mode** and **Buffer mode**.
2. The `category` column determines footprint size. This field is required when using **Buffer mode** only. 

Footprint sizes vary widely, but correlate with the type of asset (for example, power plants take up more space than restaurants). As a default, we categorize assets using the S&P "facility category" designations. Other attributes, like the name of the ultimate parent company, may be used to aggregate data. {??? Add more information about what aggregation means and how it works. ???}

| latitude | longitude | category          | ultimate_parent_name    |
|----------|-----------|-------------------|-------------------------|
| 81.07    | 33.55     | Bank Branch       | XYZ Corp                |
| ...      | ...       | ...               | ...                     |

*Table 1. Asset vector attribute table field requirements and example values for Point mode and Buffer mode.*


#### Polygon asset vector

Required for **Polygon mode**. Polygon data must be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All polygons must be in the first layer. All features in the layer must be of the `Polygon` or `MultiPolygon` type. Any attributes that exist in the original vector attribute table will be preserved in the output.

If you are running the script in **Polygon mode**, no additional fields are required by the script. {??? Is this true ???}

## Data provided for you

### footprint data by asset category
Footprint data is defined in a CSV (comma-separated value) table, where each row represents an asset category.
The first column is named `category`. The category values will be cross-referenced with the *category* field in the asset table (Table 1).
The second column is named `area`. This is the size (in square meters) of footprint to draw for assets of this category. Footprints will be drawn as a circular buffer around each asset point.

| category          | area           |
|-------------------|----------------|
| Bank Branch       | 549.7          |
| ...               | ...            |

*Table 2. Buffer table: footprint area modeled for each asset category, used in Buffer mode.*

The provided footprint areas were derived by manually estimating the footprint area of real assets on satellite imagery. We took the median of a small sample from each category. You may modify or replace this table if you wish to use different data, but it must be in CSV format, and include the required `category` and `area` fields.

### ecosystem service data
Services are defined in a CSV (comma-separated value) table, where each row represents an ecosystem service.
Columns are:
- `es_id`: A unique text (string) identifier for the ecosystem service {??? Emily, are there any requirements for this? Is it used in the output? Coordinate this language with the footprint statistics vector explanation below. ???}
- `es_value_path`: File path to a geospatial raster map of the ecosystem service {??? File type requirements ???}
- `flag_threshold`: Flagging threshold value for the ecosystem service. Pixels with an ecosystem service value greater than this threshold will be flagged. {??? is this a number? how is it determined? Need to explain flags in more detail. ???}

| es_id    | es_value_path         | flag_threshold         |
|----------|-----------------------|------------------------|
| sediment | gs://foo-sediment.tif | 123                    |
| ...      | ...                   | ...                    |

*Table 3. Ecosystem service table: defines the ecosystem service layers that will be used by the script.*

You may modify or replace this table if you wish to use different ecosystem service data, but it must be in CSV format, and include the required `es_id`, `es_value_path` and `flag_threshold` fields.

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

2. Reproject your your asset data to match the projection of your ecosystem service layers. If using the provided ecosystem service layers, reproject to Eckert IV:
```
ogr2ogr -t_srs ESRI:54012 assets_eckert.gpkg assets.gpkg
```
This can also be done in QGIS with the Warp tool, and ArcGIS using the Project tool.

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

These examples assume your ecosystem service table is named `ecosystem_service_table.csv` and your assets vector is named `assets_eckert.gpkg`. You may replace


### Point mode
`natural-capital-footprint-impact -e ecosystem_service_table.csv points assets_eckert.gpkg asset_results.gpkg company_results.csv`

In **Point mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is not known or modeled. Ecosystem service statistics are calculated under each point only.

### Buffer mode
`natural-capital-footprint-impact -e ecosystem_service_table.csv points --buffer-table buffer_table.csv assets_eckert.gpkg asset_results.gpkg company_results.csv`

In **Buffer mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is modeled by buffering each point with an area determined by the asset category in the Buffer table. Ecosystem service statistics are calculated under each footprint.

### Polygon mode
`natural-capital-footprint-impact -e ecosystem_service_table.csv polygons assets_eckert.gpkg asset_results.gpkg company_results.csv`

In **Polygon mode**, you provide the assets as footprint polygons. This mode is preferred if asset footprint data is available. Ecosystem service statistics are calculated under each footprint.

## Output formats

{??? Add details about the output fields - names, units, description, etc. An example for each would be good too. ???}

### Footprint statistics vector
The output vector attribute table is based on the point or polygon asset vector provided as input. Using the provided service list, 30 columns named `<es_id>_<statistic>` are added to the original attribute table, one for each combination of the 5 ecosystem services and these 6 statistics: 

- `max`: maximum service value within the asset footprint
- `mean`: mean service value within the asset footprint
- `sum`: sum of service values on each pixel within the asset footprint
- `count`: number of pixels within the asset footprint that have data for the service
- `nodata_count`: number of pixels within the asset footprint that are missing data for the service
- `flag`: binary value indicating whether the asset has been flagged. Assets are flagged if their `max` value is greater than the `flag_threshold` value in the ecosystem service table.

If the ecosystem service table has been modified with a different number of services, then the 6 statistics will be calculated for each of the user-defined services, with new columns defined as noted above. 

### Company statistics table
The output company table contains 

- `<es_id>_adj_sum`: Sum of `<es_id>_adj_sum` under asset footprints for each service
- `<es_id>_mean`: Mean of each ecosystem service under asset footprints
- `<es_id>_assets`: For each service, the number of assets with data
- `<es_id>_area`: Total area of asset footprints per company that are overlapping data for each service
- `<es_id>_flagged`: For each service, the number of assets flagged
- `percent_<es_id>_flagged`:  For each service, the percent of assets flagged
- `total_assets`: Total number of assets belonging to each company
- `total_area`: Total area of asset footprints belonging to each company
- `total_flagged`: Number of assets flagged (receiving a 1) for criteria 2.d in section (4) above
- `percent_total_flagged`: Percent of assets flagged in any category 

### CSV and point vector
**Point mode** produces a CSV and a point vector in geopackage (.gpkg) format. Both contain the same data. These are copies of the input data with additional columns added. There is one column added for each ecosystem service. This column contains the ecosystem service value at each point, or `NULL` if there is no data available at that location.

### polygon vector
**Buffer mode** and **Polygon mode** both produce a polygon vector in geopackage (.gpkg) format. It is a copy of the input vector with additional columns added to the attribute table. There is one column added for each combination of ecosystem service and statistic.

### Exporting to CSV
If you prefer to work with the asset-level results in CSV format, you can convert the GPKG to CSV like so:
```
ogr2ogr -f CSV asset_results.csv asset_results.gpkg
```


## References

BirdLife International (2019). Digital boundaries of Key Biodiversity Areas from the World Database of Key Biodiversity Areas. Developed by the KBA Partnership: BirdLife International, International Union for the Conservation of Nature, Amphibian Survival Alliance, Conservation International, Critical Ecosystem Partnership Fund, Global Environment Facility, Global Wildlife Conservation, NatureServe, Rainforest Trust, Royal Society for the Protection of Birds, Wildlife Conservation Society and World Wildlife Fund. September 2019 Version. Available at http://www.keybiodiversityareas.org/site/requestgis. 

Chaplin-Kramer, R. and Sharp., R.P. Nature’s Contributions to People under Potential Natural Vegetation. (Unpublished dataset). Based on models described in Chaplin-Kramer, R., Neugarten, R. A., Sharp, R. P., Collins, P. M., Polasky, S., Hole, D., et al. (2023). Mapping the planet’s critical natural assets. Nature Ecology & Evolution, 7(1), 51-61.

Damania, R., Polasky, S., Ruckelshaus, M., Russ, J., Amann, M., Chaplin-Kramer, R., Gerber, J. Hawthorne, P., Heger, M., Saleh Mamun, Ruta, G., Schmitt, R., Smith, J., Vogl, A. Wagner, F., and Zaveri, E. (2023). Nature’s Frontiers: Achieving Sustainability, Efficiency, and Prosperity with Natural Capital. Environment and Sustainable Development series. Washington, DC: World Bank. In press.

Oak Ridge National Laboratory. East View Cartographic, Inc. LandScan 2019 global population database. East View Cartographic, Inc.



