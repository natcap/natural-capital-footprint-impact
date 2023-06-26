import argparse
import logging
import math
import os
import sys
import tempfile

import geopandas as gpd
import logging
import numpy
from osgeo import gdal, ogr, osr
import pandas as pd
import pygeoprocessing
import rasterio
import taskgraph



logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


def buffer_points(point_vector_path, buffer_csv_path, attr, area_col='footprint_area'):
    """Buffer points according to a given attribute.

    Each feature in the point vector will be buffered to form a regular polygon
    approximating a circle. Its area is equal to
    `buffer_df[row[attr]]`.

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
    if point_categories - buffer_categories:
        raise ValueError(
            f'The following values of "{attr}" were found in the asset vector '
            f'but not the buffer table: {point_categories - buffer_categories}')

    for _, row in buffer_df.iterrows():
        # calculate the radius needed to draw a circle that has the given area
        buffer_radius = math.sqrt(row[area_col] / math.pi)
        mask = gdf[attr] == row[attr]
        # draw a polygon that approximates a circle
        matches = gdf[mask]
        gdf.loc[mask, 'geometry'] = gdf.loc[mask, 'geometry'].buffer(buffer_radius)

    return gdf


def point_stats(point_path, es_table_path, id_col='es_id'):
    """Find and record ecosystem service values under points.



    Args:
        point_gdf (gpd.GeoDataframe):
        out_path (str):

    Returns:
        None
    """
    # for each ecosystem services layer, use rasterio sample to get the pixel
    # value under each point. based off of this example:
    # https://geopandas.org/en/stable/gallery/geopandas_rasterio_sample.html
    logger.info('retrieving values under points...')
    point_gdf = gpd.read_file(point_path)

    if not (point_gdf.geom_type == 'Point').all():
        raise ValueError('All geometries in the asset vector must be points')

    # get list of (x, y) points
    coord_list = [
        (x,y) for x,y in zip(
            point_gdf['geometry'].x,
            point_gdf['geometry'].y
        )
    ]
    
    for _, row in pd.read_csv(es_table_path).iterrows():
        es_id = row[id_col]
        # evaluate path relative to the ES table location
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


def footprint_stats(footprint_path, es_table_path, id_col='es_id', n_workers=-1):
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
    graph = taskgraph.TaskGraph(os.getcwd(), n_workers=n_workers)

    logger.info('calculating statistics under footprints...')
    footprint_gdf = gpd.read_file(
        footprint_path, engine='pyogrio', fid_as_index=True)

    if not ((footprint_gdf.geom_type == 'Polygon') |
            (footprint_gdf.geom_type == 'MultiPolygon')).all():
        raise ValueError('All geometries in the asset vector must be polygons or multipolygons')

    es_df = pd.read_csv(es_table_path)
    es_id_to_task = {}
    for i, row in es_df.iterrows():
        es_id = row[id_col]
        path = os.path.abspath(os.path.join(
            os.path.dirname(es_table_path), row['es_value_path']))
        pixel_size = pygeoprocessing.get_raster_info(path)['pixel_size']
        es_df.loc[i, 'pixel_area'] = abs(pixel_size[0] * pixel_size[1])

        es_id_to_task[es_id] = graph.add_task(
            func=pygeoprocessing.zonal_statistics,
            args=((path, 1), footprint_path),
            target_path_list=[],
            task_name=f'{es_id} stats',
            store_result=True)

    graph.close()
    graph.join()

    for _, row in es_df.iterrows():
        es_id = row[id_col]
        zonal_stats = es_id_to_task[es_id].get()
        for stat in ['max', 'sum', 'count', 'nodata_count']:
            footprint_gdf[f'{es_id}_{stat}'] = pd.Series(
                footprint_gdf.index.to_series().map(
                    lambda fid: zonal_stats[fid][stat]))

        # use the sum to calculate the mean, but leave it out of the final result
        footprint_gdf.loc[footprint_gdf[f'{es_id}_count'] > 0, f'{es_id}_mean'] = (
            footprint_gdf[f'{es_id}_sum'] / footprint_gdf[f'{es_id}_count'])
        footprint_gdf = footprint_gdf.drop(f'{es_id}_sum', axis=1)

        # flag assets that have an ES value greater than the threshold
        footprint_gdf[f'{es_id}_flag'] = (
            footprint_gdf[f'{es_id}_max'] > row['flag_threshold'])

        # calculate the area-adjusted sum, which should be interpreted as an index
        footprint_gdf[f'{es_id}_adj_sum'] = (
            footprint_gdf[f'{es_id}_mean'] * footprint_gdf.area / row['pixel_area'])

    return footprint_gdf


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

        # total area of asset footprints per company (overlapping data or not)
        results[company]['total_area'] = company_rows['geometry'].area.sum()
        # total number of assets per company (whether overlapping data or not)
        results[company]['total_assets'] = company_rows.shape[0]

    df = pd.DataFrame(results).T
    for es_id in es_ids:
        for col in [f'{es_id}_assets', 'total_assets']:
            df[col] = df[col].astype(int)
    df.to_csv(out_path, float_format='%.5f')

aggregate_by = 'ultimate_parent_name'
attr = 'facility_category'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--ecosystem-service-table', required=True,
                        help='path to the ecosystem service table')
    parser.add_argument('mode', choices=['points', 'polygons'],
                        help=(
                            'mode of operation. in points mode, the asset vector '
                            'contains point geometries. in polygons mode, it contains '
                            'polygon geometries.'))
    parser.add_argument('-b', '--buffer-table',
                        help='buffer points according to values in this table')
    parser.add_argument('asset_vector',
                        help='path to the asset vector')
    parser.add_argument('footprint_results_path',
                        help='path to write out the asset results vector')
    parser.add_argument('company_results_path',
                        help='path to write out the aggregated results table')
    parser.add_argument('-n', '--n-workers', default=-1,
                        help='number of parallel subprocess workers to use. '
                             '0 = no subprocesses.  Set >0 '
                             'to parallelize.')
    args = parser.parse_args()

    asset_vector_srs = osr.SpatialReference()
    asset_vector_srs.ImportFromWkt(
        pygeoprocessing.get_vector_info(args.asset_vector)['projection_wkt'])

    # Make sure that all the ES layer paths are valid
    df = pd.read_csv(args.ecosystem_service_table)
    for _, row in pd.read_csv(args.ecosystem_service_table).iterrows():
        path = os.path.abspath(os.path.join(
                os.path.dirname(args.ecosystem_service_table),
                row['es_value_path']))
        if not os.path.exists(path):
            raise ValueError(
                f'The path {path} found in the ecosystem service table does not exist')

        es_layer_srs = osr.SpatialReference()
        es_layer_srs.ImportFromWkt(
            pygeoprocessing.get_raster_info(path)['projection_wkt'])
        if not es_layer_srs.IsSame(asset_vector_srs):
            raise ValueError(
                f'The asset vector ({args.asset_vector}) is in a different projection '
                f'than the ecosystem service layer {path}. All spatial inputs must have '
                'the same projection.')

    if args.buffer_table and args.mode == 'polygons':
        raise ValueError('Cannot use a buffer table in polygon mode')

    if args.mode == 'points':
        if args.buffer_table:
            footprint_gdf = buffer_points(args.asset_vector, args.buffer_table, attr, 'area')
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_footprint_path = os.path.join(tmpdir, 'footprints.gpkg')
                footprint_gdf.to_file(tmp_footprint_path, driver='GPKG', layer='footprints')

                footprint_gdf = footprint_stats(
                    tmp_footprint_path, args.ecosystem_service_table, n_workers=args.n_workers)
        else:
            point_gdf = point_stats(args.asset_vector, args.ecosystem_service_table)
            point_gdf.to_file(results_path)
            aggregate_points(point_gdf)
    else:
        footprint_gdf = footprint_stats(
            args.asset_vector, args.ecosystem_service_table, n_workers=args.n_workers)

    footprint_gdf.to_file(args.footprint_results_path, driver='GPKG', layer='footprints')
    aggregate_footprints(footprint_gdf, args.company_results_path, aggregate_by)


if __name__ == '__main__':
    main()

