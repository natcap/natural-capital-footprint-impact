# natural capital footprint impact
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Asset and company footprint impact workflow

## Introduction

This command-line script calculates metrics of the impact of human-made structures on certain ecosystem services, based on their physical footprint on the landscape. It uses point or polygon locations of corporate assets, along with raster layers of ecosystem services to generate spatial and tabular results that can be used to compare ecosystem service impacts across assets.

The ecosystem services provided are:
- `coastal_risk_reduction_service`: Relative value of coastal and marine habitats for reducing the risk of erosion and inundation from storms for people who live near the coast. 
- `nitrogen_retention_service`: Nitrogen that is retained by the landscape, keeping it out of streams, times the number of people who live downstream who may benefit from cleaner water. 
- `sediment_retention_service`: Sediment that is retained by the landscape, keeping it out of streams, times the number of people who live downstream who may benefit from cleaner water. 
- `nature_access`: The number of people within 1 hour travel distance of every pixel. 
- `kba_within_1km`: Binary value indicating whether each pixel is within 1 kilometer of a Key Biodiversity Area (KBA) or not. 

Please see the **Data provided for you > ecosystem service data** section below in this document for more information about these layers.

Some useful definitions:
- **Asset**: A unit of physical infrastructure that occupies land on Earth's surface, such as a mine, office, restaurant, cell tower, hospital, pipeline, or billboard.
- **Footprint**: The area on Earth's surface occupied by an asset.

Asset location data are usually available as point coordinates (latitude/longitude). The real footprint of an asset may be available, but usually is not. To account for differences in data availability, this script can be used in three different ways:
1. **Point mode**: Assets are provided by the user as latitude/longitude points. The actual asset footprint is not known or modeled. Ecosystem service statistics are calculated under each point only.
2. **Buffer mode**: Assets are provided by the user as latitude/longitude points. The asset footprint is modeled around each point by creating a circular buffer of an area defined by the asset type. Ecosystem service statistics are calculated under each buffered footprint.
3. **Polygon mode**: Assets are provided by the user as footprint polygons. This mode is preferred if actual asset footprint data are available. Ecosystem service statistics are calculated under each footprint.

## Data you must provide

### asset vector

#### Point asset vector

Required for both **Point mode** and **Buffer mode**. Point data must be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All points must be in the same layer. All features in the layer must be of the `Point` type. `MultiPoint`s are not allowed. Any attributes that exist in the original vector attribute table will be preserved in the output.

The asset vector layer contains an attribute table, where each row represents an asset. The following fields are used by the script:

1. The `category` column determines footprint size. This field is required when using **Buffer mode** only. Footprint sizes vary widely, but correlate with the type of asset (for example, power plants take up more space than restaurants). As a default, we categorize assets using the S&P "facility category" designations, which corresponds to the default data provided in the Buffer Table (Table 3).
2. The `company` attribute is required for both **Point mode** and **Buffer mode**, and is used to aggregate results. Assets belonging to the same `company` will be grouped together when calculating the aggregate statistics.

Field names must be spelled exactly as shown above, with no extra spaces or characters.

| FID  | <...other non-script related attributes...>   | category           | company        |
|------|-----------------------------------------------|--------------------|----------------|
| 0    | <...non-script-related value...>              | Bank Branch        | XYZ Corp       |
| 1    | ...                                           | ...                | ....           |

*Table 1. Point asset vector attribute table example.*

#### Polygon asset vector

Required for **Polygon mode**. Polygon data must be provided in a [GDAL-supported vector format](https://gdal.org/drivers/vector/index.html). All polygons must be in the same layer. All features in the layer must be of the `Polygon` or `MultiPolygon` type. Any attributes that exist in the original vector attribute table will be preserved in the output.

The `company` attribute is reqired for **Polygon mode**, and is used to aggregate results. Assets belonging to the same `company` will be grouped together when calculating the aggregate statistics. The field name, `company`, must be spelled exactly as shown here, with no extra spaces or characters.

| FID | <...other non-script related attributes...>   | company        |
|-----|-----------------------------------------------|----------------|
| 0   | <...non-script-related value...>              | XYZ Corp       |
| 1   | ...                                           | ....           |

*Table 2. Polygon asset vector attribute table example.*

## Data provided for you

### footprint data by asset category
Footprint buffer area data are defined in a CSV (comma-separated value) table (Table 3), where each row represents an asset category.
The first column is named `category`. The category values will be cross-referenced with the *category* field in the Asset Table (Table 1).
The second column is named `area`. This is the area (in square meters) of footprint to draw for assets of this category. Footprints will be drawn as a circular buffer around each asset point.

| category          | area           |
|-------------------|----------------|
| Bank Branch       | 5073.7         |
| ...               | ...            |

*Table 3. Buffer table: footprint area (in square meters) modeled for each asset category, used in Buffer mode.*

The provided footprint areas were derived by manually estimating the footprint area of real assets from  satellite imagery. We took the median of a small sample from each category. You may modify or replace this table if you wish to use different data, but they must be in CSV format, and include the required `category` and `area` fields.

### ecosystem service data

Ecosystem service data are provided as geospatial raster layers (such as TIFFs), where each pixel has a value representing the quantity of service provided at that pixel. 

Five raster datasets are provided for use with this script. Four ecosystem service rasters - sediment retention, nitrogen retention, coastal risk reduction, nature access - and one biodiversity raster - Key Biodiversity Areas (KBAs). In order to use this script, you must either download one or more of these layers, or provide your own. Following is a description of each provided layer, along with links for downloading them. 

- `coastal_risk_reduction_service`: Relative value of coastal and marine habitats for reducing the risk of erosion and inundation from storms for people who live near the coast. Risk reduction is calculated using the InVEST Coastal Vulnerability model. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. Values are unitless, representing a relative index of risk reduction times the number of people who benefit. [Download link for coastal risk](https://drive.google.com/file/d/1zhM8vvQiFW8xtkpH7tnIFtZt-0yydsZ0/view?usp=drive_link). License for using these data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- `nature_access`: The number of people within 1 hour travel distance of every pixel. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. [Download link for nature access](https://drive.google.com/file/d/179tYugUOHy_fNWaTN1BGUMERF231TAxr/view?usp=drive_link). License for using these data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- `nitrogen_retention_service`: Nitrogen that is retained by the landscape, keeping it out of streams, times the number of people who live downstream who may benefit from cleaner water. Nitrogen retention is calculated using the InVEST Nutrient Delivery Ratio (NDR) model. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. Values are unitless, representing kilograms of nitrogen retained times number of people who benefit. [Download link for nitrogen retention](https://drive.google.com/file/d/1YWqL5--7i77gjdXZO22p5lHKK5BSTXGY/view?usp=drive_link). License for using these data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- `sediment_retention_service`: Sediment that is retained by the landscape, keeping it out of streams, times the number of people who live downstream who may benefit from cleaner water. Sediment retention is calculated using the InVEST Sediment Delivery Ratio (SDR) model. Modeling by Chaplin-Kramer and Sharp (2023). Population is from Landscan 2019. Values are unitless, representing tons of sediment retained times number of people who benefit. [Download link for sediment retention](https://drive.google.com/file/d/1muGnbHeOVpA0osaUoPdrA02m1b5Ugn5u/view?usp=drive_link). License for using these data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- `kba_within_1km`: Binary value indicating whether each pixel is within 1 kilometer of a Key Biodiversity Area (KBA) or not (1 = yes, 0 = no). Adapted from data created for Damania et al. (2023). KBAs are from BirdLife International (2019). [Download link for KBAs](https://drive.google.com/file/d/1oWv-QGWV2wkzma5p6dvUVsOInmcOUQ4K/view?usp=drive_link). The license for using these data is provided in the [Key Biodiversity Areas Terms of Service](https://www.keybiodiversityareas.org/termsofservice). Of note, they may not be used for commercial purposes.

The script requires that all services to be analyzed are listed in a CSV (comma-separated value) table, where each row represents an ecosystem service.
Required columns are:
- `es_id`: A unique identifier for the ecosystem service, which consists of any ASCII characters and may be of any length. This identifier is used to label the output statistics. The `es_id`s for the provided data are: `coastal_risk_reduction_service`, `nitrogen_retention_service`, `sediment_retention_service`, `nature_access`, `endemic_biodiversity`, `redlist_species`, `species_richness`, `kba_within_1km`. 
- `es_value_path`: File path to a GDAL-supported geospatial raster map of the ecosystem service. These may be given as paths that are relative to the location of the CSV file, or may be given as absolute paths.
- `flag_threshold`: Threshold value of interest for the ecosystem service. Pixels with an ecosystem service value greater than this threshold will be flagged, and results will be provided indicating whether the service value for each asset exceeds this threshold. In the provided data, we used the 90th percentile value as the threshold for each ecosystem service, except for Coastal Risk Reduction and KBA, for which the threshold was 0.

| es_id    | es_value_path                                                    | flag_threshold         |
|----------|----------------------------------------------------------------  |------------------------|
| sediment | ES_layers/sediment_retention_for_downstream_populations.tif      | 96485936               |
| ...      | ...                                                              | ...                    |

*Table 4. Ecosystem service table example: defines the ecosystem service layers that will be used by the script.*

You may modify or replace this table, with the requirement that it must be in CSV format, and include the required `es_id`, `es_value_path` and `flag_threshold`, fields. This table must be modified if you are using your own service layers or changing the path location of the default layers.

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
1. If your asset point data are in CSV format, convert it to a GDAL-supported vector format such as GeoPackage (GPKG):
```
ogr2ogr -s_srs EPSG:4326 -t_srs EPSG:4326 -oo X_POSSIBLE_NAMES=longitude -oo Y_POSSIBLE_NAMES=latitude assets.gpkg assets.csv
```
To do this in QGIS, use the *Add Delimited Text Layer* tool to add the CSV data as a point layer, then *Export > Save Features As* to save the layer to a GeoPackage.

In ArcGIS Pro, import the CSV data to a point layer using the *XY Data to Point* tool. This will create a point shapefile that you can use instead of a GeoPackage. 

2. Reproject your asset data to match the projection of your ecosystem service layers. If using the provided ecosystem service layers, assets must be projected in Eckert IV (ESRI:54012):
```
ogr2ogr -t_srs ESRI:54012 assets_eckert.gpkg assets.gpkg
```
This can also be done in QGIS with the Warp tool, and ArcGIS using the Project tool.

3. Run the workflow:
```
natural-capital-footprint-impact -e ECOSYSTEM_SERVICE_TABLE {points,polygons} [-b BUFFER_TABLE] asset_vector
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
                        buffer asset points according to values in this table 
```

The examples below assume your ecosystem service table is named `ecosystem_service_table.csv` and your assets vector is named `assets_example.gpkg`. You may use any other valid file path instead.

### Point mode
`natural-capital-footprint-impact -e ecosystem_service_table.csv points assets_example.gpkg asset_results.gpkg company_results.csv`

In **Point mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is not known or modeled. Ecosystem service statistics are calculated under each point only.

When run in point mode, the script performs these steps:
1. Calculates ecosystem service values at the location of each asset point.
2. Groups asset points by their `company` attribute.
3. Aggregates statistics about the asset points for each `company`.

### Point buffer mode
`natural-capital-footprint-impact -e ecosystem_service_table.csv points --buffer-table buffer_table.csv assets_example.gpkg asset_results.gpkg company_results.csv`

In **Buffer mode**, you provide the assets as latitude/longitude coordinate points. The asset footprint is modeled by buffering each point with an area determined by the asset category in the Buffer Table. Ecosystem service statistics are calculated under each footprint.

When run in point buffer mode, the script performs these steps:
1. Cross-references the asset vector with the buffer table on the `category` attribute to get the buffer area for each asset.
2. Buffers each asset point to form an asset footprint polygon with the appropriate buffer area. The buffer polygon is a many-sided regular polygon approximating a circle.
3. Calculates statistics about each ecosystem service within the area of each asset footprint. See note below for caveats.
4. Groups asset footprints by their `company` attribute.
5. Aggregates statistics about the assets for each `company`.

### Polygon mode
`natural-capital-footprint-impact -e ecosystem_service_table.csv polygons assets_example.gpkg asset_results.gpkg company_results.csv`

In **Polygon mode**, you provide the assets as footprint polygons. This mode is preferred if asset footprint data are available. Ecosystem service statistics are calculated under each footprint.

When run in polygon mode, the script performs these steps:
1. Calculates statistics about each ecosystem service within the area of each asset footprint. See note below for caveats.
2. Groups asset footprints by their `company` attribute.
3. Aggregates statistics about the assets for each `company`.

### Caveat about footprint statistics
Because of the coarse resolution of the ecosystem service layers relative to typical asset footprint sizes, and the way that zonal statistics are calculated in the underlying library `pygeoprocessing`, some results at the asset level may be non-intuitive. `pygeoprocessing.zonal_statistics` calculates statistics using this algorithm:
```
If the polygon overlaps the centerpoint of at least one pixel:
    Statistics are only calculated from the set of pixel(s) whose centerpoints fall within the polygon
If the polygon does not overlap the centerpoint of any pixel:
    Statistics are calculated from the set of pixel(s) that intersect the bounding box of the polygon
```
If this causes problems, you may try resampling the ecosystem service layers to a finer (smaller) resolution.

## Output formats

### Footprint statistics vector
The output vector attribute table is based on the point or polygon asset vector provided as input. Several statistics are calculated for each ecosystem service:

**In point mode:**
- `<es_id>_max`: maximum service value within the asset footprint
- `<es_id>_flag`: binary value indicating whether the asset has been flagged. Assets are flagged if their `<es_id>_max` value is greater than the corresponding `flag_threshold` value in the ecosystem service table.

Using the provided service list, 10 columns named `<es_id>_<statistic>` are added to the original attribute table, one for each combination of the 5 ecosystem services and these 2 statistics.

Example output attribute table for point mode:
| FID | kba_max | kba_flag | ... |
|-----|---------|----------|-----|
| 1   | 1       | 1        | ... |
| 2   | 0       | 0        | ... | 
  

**In point buffer mode and polygon mode:**
- `<es_id>_max`: maximum service value within the asset footprint.
- `<es_id>_mean`: mean service value within the asset footprint.
- `<es_id>_adj_sum`: Area-adjusted sum of service values on each pixel within the asset footprint. This is `<es_id>_mean` multiplied by the asset footprint area.
- `<es_id>_count`: number of pixels within the asset footprint that have data for the service.
- `<es_id>_nodata_count`: number of pixels within the asset footprint that are missing data for the service.
- `<es_id>_flag`: binary value indicating whether the asset has been flagged. Assets are flagged if their `<es_id>_max` value is greater than the corresponding `flag_threshold` value in the ecosystem service table.

Note: These statistics are derived from the set of pixels that is calculated as described above, see "Caveats about footprint statistics".

Using the provided service list, 30 columns named `<es_id>_<statistic>` are added to the original attribute table, one for each combination of the 5 ecosystem services and these 6 statistics.

Example output attribute table for buffer mode and polygon mode:
| FID | kba_max | kba_mean | kba_adj_sum | ... |
|-----|---------|----------|-------------|-----|
| 1   | 1       | 0.25     | 0.3         | ... |
| 2   | 0       | 0        | 0           | ... |

The units for the `<es_id>`, `<es_id>_max`, `<es_id>_mean`, and `<es_id>_adj_sum` values will vary depending on the service. If you are using the default/provided services, see the introduction in this Readme for a description of these services and their units. If the ecosystem service table has been modified with a different number of services, then the statistics will be calculated for each of the user-defined services, with new columns defined as noted above. 



### Company statistics table
The output company table contains 

- `<es_id>_adj_sum`: Sum of `<es_id>_adj_sum` under asset footprints for each service
- `<es_id>_mean`: Mean of each ecosystem service under asset footprints
- `<es_id>_assets`: For each service, the number of assets with data
- `<es_id>_area`: Total area of asset footprints per company that are overlapping data for each service
- `<es_id>_flagged`: For each service, the number of assets flagged
- `percent_<es_id>_flagged`: For each service, the percent of assets flagged
- `total_assets`: Total number of assets belonging to each company
- `total_area`: Total area (in square meters) of asset footprints belonging to each company
- `total_flagged`: Number of assets flagged (receiving a 1) by criteria defined above
- `percent_total_flagged`: Percent of assets flagged in any category

Again, the units for the `<es_id>_adj_sum` and `<es_id>_mean` values will vary depending on the service. If you are using the default/provided services, see the introduction in this Readme for a description of these services and their units.

Example:
| company  | kba_adj_sum | kba_mean | kba_assets | ... |
|----------|-------------|----------|------------|-----|
| XYZ Corp | 0           | 0        | 3          | ... |
| AAA Inc. | 0.57        | 0.7      | 13         | ... |

### CSV and point vector
**Point mode** produces a CSV and a point vector in geopackage (.gpkg) format. Both contain the same data. These are copies of the input data with additional columns added. There is one column added for each ecosystem service. This column contains the ecosystem service value at each point, or `NULL` if there are no data available at that location.

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



