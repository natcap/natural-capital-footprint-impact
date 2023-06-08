import math
import os
import sys

import geopandas as gpd
import logging
import numpy
from osgeo import ogr, gdal
import pandas as pd
import pygeoprocessing
import rasterio

logger = logging.getLogger()

def point_stats(point_path, es_table_path, id_col='es_id'):
    """Find and record ecosystem service values under points.

    Based off of this example:
    https://geopandas.org/en/stable/gallery/geopandas_rasterio_sample.html

    Args:
        point_gdf (gpd.GeoDataframe):
        out_path (str):

    Returns:
        None
    """
    # for each ecosystem services layer
    # use rasterio sample to get the pixel value under each point.
    # this is done with rasterio sample
    # we must first convert points to the raster CRS to use rasterio sample
    # 
    logger.info('retrieving values under points...')
    point_gdf = gpd.read_file(point_path)

    if not (point_gdf.geom_type == 'Point').all():
        raise ValueError('All geometries in the asset vector must be points')

    # get list of (x, y) points
    coord_list = [
        (x,y) for x,y in zip(
            point_gdf['geometry'].x ,
            point_gdf['geometry'].y
        )
    ]
    
    for _, row in pd.read_csv(es_table_path).iterrows():
        es_id = row[id_col]
        es_dataset = rasterio.open(
            os.path.abspath(os.path.join(
                os.path.dirname(es_table_path), row['es_value_path'])))

        # get the pixel value under each point
        point_values = numpy.ma.MaskedArray(
            list(es_dataset.sample(coord_list, masked=True)))
        point_values[point_values is masked] = numpy.nan

        point_gdf[es_id] = point_values
        point_gdf[f'{es_id}_flag'] = point_values > row['flag_threshold']

    return point_gdf


def footprint_stats(footprint_path, es_table_path, id_col='es_id'):
    """Calculate and record stats of ecosystem service values under footprints.

    Args:
        footprint_path (str): path to a GDAL-supported footprint polygon vector
        es_table_path (str): path to the ecosystem service CSV, which should
            have the following columns: es_id (the unique identifier for
            each ecosystem service); path (the path to the global ecosystem
            service raster); and the numbers 0 through 100, storing the
            integer percentile values for each ecosystem service globally.
        out_path (str): path to write out the resulting footprint stats vector

    Returns:
        None
    """
    logger.info('calculating statistics under footprints...')
    footprint_gdf = gpd.read_file(
        footprint_path, engine='pyogrio', fid_as_index=True)

    if not ((footprint_gdf.geom_type == 'Polygon') |
            (footprint_gdf.geom_type == 'MultiPolygon')).all():
        print(footprint_gdf.geom_type.unique())
        raise ValueError('All geometries in the asset vector must be polygons or multipolygons')

    stats = ['max', 'sum', 'count', 'nodata_count']
    for _, row in pd.read_csv(es_table_path).iterrows():
        es_id = row[id_col]
        zonal_stats = pygeoprocessing.zonal_statistics(
            (os.path.abspath(os.path.join(os.path.dirname(es_table_path),
                                          row['es_value_path'])), 1),
            footprint_path)

        for stat in stats:
            footprint_gdf[f'{es_id}_{stat}'] = pd.Series(
                footprint_gdf.index.to_series().map(
                    lambda fid: zonal_stats[fid][stat]))

        footprint_gdf[f'{es_id}_flag'] = (
            footprint_gdf[f'{es_id}_max'] > row['flag_threshold'])

    return footprint_gdf


def buffer_points(point_vector_path, buffer_csv_path, attr, area_col='footprint_area'):
    """Buffer points according to a given attribute.
    
    For a given row in `gdf`, `row['geometry']` will be buffered to form a
    regular polygon approximating a circle. Its area is equal to
    `buffer_df[row[attr]]`.

    For example, suppose your attribute is called 'facility_category'. Then
    the point vector attribute table should contain a `facility_category`
    column.
    
    Args:
        point_vector_path: path to a GDAL-supported point vector
        buffer_csv_path: maps attribute values to footprint areas.
            must contain two columns: `facility_category` and 'footprint_area'.
            areas must be provided in square meters.
        attr:
    
    Returns:
        a copy of the input geodataframe, where each row's `geometry` has been 
        replaced with a circular footprint
        
    Raises:
        ValueError if any geometry in the vector is not a point

        ValueError if there are `facility_category` values in the point vector
            that are not found in the buffer table
    """
    logger.info('buffering points to create footprints...')
    gdf = gpd.read_file(point_vector_path)
    if not (gdf.geom_type == 'Point').all():
        raise ValueError('All geometries in the asset vector must be points')

    buffer_df = pd.read_csv(buffer_csv_path)

    point_categories = set(gdf[attr].unique())
    buffer_categories = set(buffer_df[attr].unique())
    # if point_categories - buffer_categories:
    #     raise ValueError(
    #         f'The following values of "{attr}" were found in the asset vector '
    #         f'but not the buffer table: {point_categories - buffer_categories}')

    for _, row in buffer_df.iterrows():
        # calculate the radius needed to draw a circle that has the given area
        buffer_radius = math.sqrt(row[area_col] / math.pi)
        mask = gdf[attr] == row[attr]
        # draw a polygon that approximates a circle
        matches = gdf[mask]
        gdf.loc[mask, 'geometry'] = gdf.loc[mask, 'geometry'].buffer(buffer_radius)

    return gdf


def aggregate_footprints(gdf, out_path, aggregate_by):
    """Aggregate footprint stats up to the company level.

    Args:
        footprint_path (str): path to a GDAL-supported footprint polygon vector
        out_path (str): path to write out the CSV table of aggregated data
        aggregate_by (str): footprint attribute to aggregate by

    Returns:
        None
    """
    logger.info('aggregating...')
    es_ids = [x[:-4] for x in gdf.columns if x.endswith('sum')]
    results = {}
    vals = gdf[aggregate_by].unique()

    for company in vals:
        company_rows = gdf[gdf[aggregate_by] == company]
        results[company] = {}
        total_flags = pd.Series([False for _ in range(company_rows.shape[0])])
        for es_id in es_ids:

            # company assets that overlap this ecosystem service
            valid_company_rows = (
                company_rows[company_rows[f'{es_id}_count'] > 0])

            # sum of ES pixel values under all asset footprints per company
            results[company][f'{es_id}_sum'] = (
                valid_company_rows[f'{es_id}_sum'].sum())

            # mean of ES pixel values under all asset footprints per company
            n_valid_es_pixels = valid_company_rows[f'{es_id}_count'].sum()
            if n_valid_es_pixels == 0:
                results[company][f'{es_id}_mean'] = None
            else:
                # sum of es pixel values / the number of es pixel values
                results[company][f'{es_id}_mean'] = (
                    valid_company_rows[f'{es_id}_sum'].sum() /
                    n_valid_es_pixels)

            # total area of asset footprints per company that are overlapping data
            results[company][f'{es_id}_area'] = (
                valid_company_rows['geometry'].area.sum())
            # total number of assets per company that are overlapping data
            results[company][f'{es_id}_assets'] = valid_company_rows.shape[0]

            results[company][f'{es_id}_flags'] = valid_company_rows[f'{es_id}_flag'].sum()

            results[company][f'percent_{es_id}_flagged'] = (
                results[company][f'{es_id}_flags'] /
                results[company][f'{es_id}_assets'] * 100)

            total_flags = total_flags | company_rows[f'{es_id}_flag']


        # total area of asset footprints per company (overlapping data or not)
        results[company]['total_area'] = company_rows['geometry'].area.sum()
        # total number of assets per company (whether overlapping data or not)
        results[company]['total_assets'] = company_rows.shape[0]

        results[company]['total_flags'] = total_flags.sum()

        results[company]['percent_total_flagged'] = (
            results[company]['total_flags'] / results[company]['total_assets'] * 100)

    df = pd.DataFrame(results).T
    df.to_csv(out_path)


def aggregate_points(footprint_path, out_path, aggregate_by):
    """Aggregate footprint stats up to the company level.

    Args:
        footprint_path (str): path to a GDAL-supported footprint polygon vector
        out_path (str): path to write out the CSV table of aggregated data
        aggregate_by (str): footprint attribute to aggregate by

    Returns:
        None
    """
    logger.info('aggregating...')
    gdf = gpd.read_file(footprint_path)
    es_ids = [x[:-4] for x in gdf.columns if x.endswith('sum')]
    results = {}
    vals = gdf[aggregate_by].unique()
    for company in vals:
        company_rows = gdf[gdf[aggregate_by] == company]
        results[company] = {}
        for es_id in es_ids:

            # company assets that overlap this ecosystem service
            valid_company_rows = (
                company_rows[company_rows[f'{es_id}_count'] > 0])

            # sum of ES pixel values under all asset footprints per company
            results[company][f'{es_id}_sum'] = (
                valid_company_rows[f'{es_id}_sum'].sum())

            # mean of ES pixel values under all asset footprints per company
            n_valid_es_pixels = valid_company_rows[f'{es_id}_count'].sum()
            if n_valid_es_pixels == 0:
                results[company][f'{es_id}_mean'] = None
            else:
                # sum of es pixel values / the number of es pixel values
                results[company][f'{es_id}_mean'] = (
                    valid_company_rows[f'{es_id}_sum'].sum() /
                    n_valid_es_pixels)

            # total area of asset footprints per company that are overlapping data
            results[company][f'{es_id}_area'] = (
                valid_company_rows['geometry'].area.sum())
            # total number of assets per company that are overlapping data
            results[company][f'{es_id}_assets'] = valid_company_rows.shape[0]

            # number of assets whose mean value is above the 90th percentile
            results[company][f'{es_id}_count_mean>90th'] = numpy.sum(
                valid_company_rows[f'mean_{es_id}_percentile'] > 90)
            # number of assets whose max value is above the 90th percentile
            results[company][f'{es_id}_count_max>90th'] = numpy.sum(
                valid_company_rows[f'max_{es_id}_percentile'] > 90)
            # percent of assets whose mean value is above the 90th percentile
            results[company][f'{es_id}_%_mean>90th'] = numpy.sum(
                valid_company_rows[f'mean_{es_id}_percentile'] > 90) / company_rows.shape[0] * 100

        # total area of asset footprints per company (overlapping data or not)
        results[company]['total_area'] = company_rows['geometry'].area.sum()
        # total number of assets per company (whether overlapping data or not)
        results[company]['total_assets'] = company_rows.shape[0]

    df = pd.DataFrame(results).T
    for es_id in es_ids:
        for col in [f'{es_id}_assets', f'{es_id}_count_mean>90th',
                    f'{es_id}_count_max>90th', 'total_assets']:
            df[col] = df[col].astype(int)
    df.to_csv(out_path, float_format='%.5f')

