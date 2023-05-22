import argparse
import logging
import os
import sys
import tempfile

from .src import point_stats, point_flags, \
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
    parser.add_argument('-e', '--ecosystem-service-table', required=True)
    parser.add_argument('--footprint-results-path', default='footprint_stats.gpkg')
    parser.add_argument('--company-results-path', default='company_stats.csv')
    subparsers = parser.add_subparsers(help='execution mode', dest='mode', required=True)
    points_parser = subparsers.add_parser('points', help='provide asset coordinates')
    points_parser.add_argument('--buffer-table', help='buffer points according to values in table')
    points_parser.add_argument('asset_vector', help='path to asset point vector')
    polygons_parser = subparsers.add_parser('polygons', help='provide asset footprint polygons')
    polygons_parser.add_argument('asset_vector', help='path to asset polygon vector')
    args = parser.parse_args()

    if args.mode == 'points':
        if args.buffer_table:
            footprint_gdf = buffer_points(args.asset_vector, args.buffer_table, attr, 'area')
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_footprint_path = os.path.join(tmpdir, 'footprints.gpkg')
                footprint_gdf.to_file(tmp_footprint_path, driver='GPKG', layer='footprints')
                footprint_gdf = footprint_stats(tmp_footprint_path, args.ecosystem_service_table)
        else:
            point_gdf = point_stats(args.asset_vector, args.ecosystem_service_table)
            point_gdf = point_flags(point_gdf, args.ecosystem_service_table)
            point_gdf.to_file(results_path)
            aggregate_points(point_gdf)
    else:
        footprint_gdf = footprint_stats(args.asset_vector, args.ecosystem_service_table)

    footprint_gdf.to_file(args.footprint_results_path, driver='GPKG', layer='footprints')
    aggregate_footprints(footprint_gdf, args.company_results_path, aggregate_by)

if __name__ == '__main__':
    main()
