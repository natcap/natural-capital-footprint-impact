import unittest
from unittest import mock
import tempfile
import shutil
import os
import textwrap

import fiona
from fiona.crs import from_epsg
import geopandas
from shapely.geometry import Point, Polygon, mapping

from osgeo import gdal
from osgeo import osr
import numpy
import numpy.random
import numpy.testing
import pygeoprocessing


class FootprintImpactWorkflowTests(unittest.TestCase):
    """Tests for the Carbon Model ARGS_SPEC and validation."""

    def setUp(self):
        """Create a temporary workspace."""
        self.workspace_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Remove the temporary workspace after a test."""
        shutil.rmtree(self.workspace_dir)

    def test_buffer_points(self):
        from .buffer_points import buffer_points
        asset_path = os.path.join(self.workspace_dir, 'assets.gpkg')
        buffer_table_path = os.path.join(self.workspace_dir, 'buffer.csv')
        out_path = os.path.join(self.workspace_dir, 'out.gpkg')
        schema = {
            'geometry': 'Point',
            'properties': {
                'id': 'int',
                'foo_category': 'str'
            }
        }
        with fiona.open(asset_path, 'w', 'GPKG', schema=schema, crs=from_epsg(8857)) as out:
            point = Point([0, 0])
            out.write({
              'geometry': mapping(point),
              'properties': {
                  'id': 1,
                  'foo_category': 'x'
              }
            })
        with open(buffer_table_path, 'w') as table:
            table.write(textwrap.dedent(
                """
                foo_category,footprint_area
                x,103
                """))
        buffer_points(asset_path, buffer_table_path, out_path)

        for _, record in fiona.open(out_path).items():
            self.assertEqual(record['geometry']['type'], 'Polygon')
            polygon = Polygon(record['geometry']['coordinates'][0])
            print(polygon)
            self.assertEqual(polygon.area, 103)
            # confusingly, equals_exact tests equality with a tolerance
            self.assertTrue(polygon.centroid.equals_exact(point, 1e-6))

    @mock.patch('pygeoprocessing.zonal_statistics')
    def test_footprint_stats(self, zonal_statistics):
        from .footprint_stats import footprint_stats
        zonal_statistics.return_value = {1: {'sum': 42, 'count': 8}}

        footprint_path = os.path.join(self.workspace_dir, 'assets.gpkg')
        es_table_path = os.path.join(self.workspace_dir, 'services.csv')
        out_path = os.path.join(self.workspace_dir, 'out.gpkg')
        schema = {
            'geometry': 'Polygon',
            'properties': {
                'id': 'int',
                'foo_category': 'str'
            }
        }
        with fiona.open(footprint_path, 'w', 'GPKG', schema=schema, crs=from_epsg(8857)) as out:
            polygon = Polygon([[0, 0], [2.5, 0], [2.75, 2.75], [0, 0]])

            out.write({
              'geometry': mapping(polygon),
              'properties': {
                  'id': 1,
                  'foo_category': 'x'
              }
            })
        with open(es_table_path, 'w') as table:
            table.write(textwrap.dedent(
                """
                es_id,path
                foo,foo.tif
                """))
        footprint_stats(footprint_path, es_table_path, out_path)

        for _, record in fiona.open(out_path).items():
            print(dict(record['properties']))
            self.assertEqual(record['geometry']['type'], 'Polygon')
            out_polygon = Polygon(record['geometry']['coordinates'][0])
            self.assertTrue(polygon.equals(out_polygon))
            self.assertTrue('foo_mean' in record['properties'])
            self.assertEqual(record['properties']['foo_mean'], 5.25)

    def test_bin_percentiles(self):
        from .bin_percentiles import bin_to_percentile
        footprint_path = os.path.join(self.workspace_dir, 'assets.gpkg')
        percentile_table_path = os.path.join(self.workspace_dir, 'services.csv')
        out_path = os.path.join(self.workspace_dir, 'out.gpkg')
        schema = {
            'geometry': 'Polygon',
            'properties': {
                'id': 'int',
                'foo_category': 'str',
                'foo_mean': 'float'
            }
        }
        with fiona.open(footprint_path, 'w', 'GPKG', schema=schema, crs=from_epsg(8857)) as out:
            polygon = Polygon([[0, 0], [2.5, 0], [2.75, 2.75], [0, 0]])
            out.write({
              'geometry': mapping(polygon),
              'properties': {
                  'id': 1,
                  'foo_category': 'x',
                  'foo_mean': 0.063
              }
            })
        with open(percentile_table_path, 'w') as table:
            table.write(textwrap.dedent(
                """
                es_id,path,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100
                foo,foo.tif,0,.01,.02,.03,.04,.05,.06,.07,.08,.09,.1,.11,.12,.13,.14,.15,.16,.17,.18,.19,.2,.21,.22,.23,.24,.25,.26,.27,.28,.29,.3,.31,.32,.33,.34,.35,.36,.37,.38,.39,.4,.41,.42,.43,.44,.45,.46,.47,.48,.49,.5,.51,.52,.53,.54,.55,.56,.57,.58,.59,.6,.61,.62,.63,.64,.65,.66,.67,.68,.69,.7,.71,.72,.73,.74,.75,.76,.77,.78,.79,.8,.81,.82,.83,.84,.85,.86,.87,.88,.89,.9,.91,.92,.93,.94,.95,.96,.97,.98,.99,1
                """))

        bin_to_percentile(footprint_path, percentile_table_path, out_path)
        gdf = geopandas.read_file(out_path)
        print(gdf)


