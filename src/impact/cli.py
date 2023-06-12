import argparse
import logging
import os
import sys
import tempfile
import pandas as pd

from .src import point_stats, \
    buffer_points, footprint_stats, aggregate_points, aggregate_footprints

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

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
    args = parser.parse_args()

    # Make sure that all the ES layer paths are valid
    df = pd.read_csv(args.ecosystem_service_table)
    for _, row in pd.read_csv(args.ecosystem_service_table).iterrows():
        path = os.path.abspath(os.path.join(
                os.path.dirname(args.ecosystem_service_table),
                row['es_value_path']))
        assert os.path.exists(path)

    if args.buffer_table and args.mode == 'polygons':
        raise ValueError('Cannot use a buffer table in polygon mode')

    if args.mode == 'points':
        if args.buffer_table:
            footprint_gdf = buffer_points(args.asset_vector, args.buffer_table, attr, 'area')
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_footprint_path = os.path.join(tmpdir, 'footprints.gpkg')
                footprint_gdf.to_file(tmp_footprint_path, driver='GPKG', layer='footprints')

                footprint_gdf = footprint_stats(tmp_footprint_path, args.ecosystem_service_table)
        else:
            point_gdf = point_stats(args.asset_vector, args.ecosystem_service_table)
            point_gdf.to_file(results_path)
            aggregate_points(point_gdf)
    else:
        footprint_gdf = footprint_stats(args.asset_vector, args.ecosystem_service_table)

    footprint_gdf.to_file(args.footprint_results_path, driver='GPKG', layer='footprints')
    aggregate_footprints(footprint_gdf, args.company_results_path, aggregate_by)

if __name__ == '__main__':
    main()
