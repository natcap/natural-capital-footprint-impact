import argparse
import logging
import os
import sys
import tempfile

from buffer_points import buffer_points
from footprint_stats import footprint_stats
from bin_percentiles import bin_to_percentile
from aggregate import aggregate

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

parser = argparse.ArgumentParser()
parser.add_argument('--asset-vector')
parser.add_argument('--buffer-table')
parser.add_argument('--ecosystem-service-table')
parser.add_argument('out_path')
args = parser.parse_args()

aggregate_by = 'ultimate_parent_name'
attr = 'facility_category'

workspace_dir = '/Users/emily/Documents/footprint_wksp4'
os.makedirs(workspace_dir)

footprint_path = os.path.join(workspace_dir, 'footprints.gpkg')
footprints_with_stats_path = os.path.join(workspace_dir, 'footprints_with_stats.gpkg')
footprints_with_binned_stats_path = os.path.join(workspace_dir, 'footprints_with_binned_stats.gpkg')

logger.info('buffer points to create footprints...')
buffer_points(args.asset_vector, args.buffer_table, footprint_path, attr, 'area')
logger.info('calculate ecosystem service stats under footprints...')
footprint_stats(footprint_path, args.ecosystem_service_table, footprints_with_stats_path)
logger.info('bin against global percentiles...')
bin_to_percentile(footprints_with_stats_path, args.ecosystem_service_table, footprints_with_binned_stats_path)
logger.info('aggregate...')
aggregate(footprints_with_binned_stats_path, args.out_path, aggregate_by)
