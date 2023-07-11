import argparse
import unittest
from unittest import mock
import tempfile
import shutil
import os
import textwrap

import fiona
from fiona.crs import from_epsg
import pandas
import geopandas
import geopandas.testing
from shapely.geometry import Point, Polygon, mapping

from osgeo import gdal
from osgeo import osr, ogr
import numpy
import numpy.random
import numpy.testing
import pygeoprocessing


class FootprintImpactWorkflowTests(unittest.TestCase):

    def setUp(self):
        """Create a temporary workspace."""
        self.workspace_dir = tempfile.mkdtemp()
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32731)  # WGS84/UTM zone 31s
        self.wkt = srs.ExportToWkt()
        self.es_1_path = os.path.join(self.workspace_dir, 'es_1.tif')
        self.es_2_path = os.path.join(self.workspace_dir, 'es_2.tif')

    def tearDown(self):
        """Remove the temporary workspace after a test."""
        shutil.rmtree(self.workspace_dir)

    def make_es_inputs(self):
        es_1_array = numpy.array([i for i in range(100)], dtype=numpy.int16).reshape((10, 10))
        pygeoprocessing.numpy_array_to_raster(
            es_1_array, 255, (2, -2), (2, -2), self.wkt, self.es_1_path)

        es_2_array = numpy.array([[i/2 for _ in range(10)] for i in range(7)], dtype=numpy.float32)
        es_2_array[1] = [255 for _ in range(10)]
        pygeoprocessing.numpy_array_to_raster(
            es_2_array, 255, (2, -2), (2, -2), self.wkt, self.es_2_path)

        self.es_table_path = os.path.join(self.workspace_dir, 'es_table.csv')
        pandas.DataFrame({
            'es_id': ['es_1', 'es_2'],
            'es_value_path': [self.es_1_path, self.es_2_path],
            'flag_threshold': [90, 3]
        }).to_csv(self.es_table_path)

    def test_complete_run_point_mode(self):
        from impact.src import execute

        self.make_es_inputs()

        asset_points_path = os.path.join(self.workspace_dir, 'assets.geojson')
        asset_points = [Point(5.55, -4.51), Point(12.9, -12.9), Point(6.09, -20.06)]
        pygeoprocessing.shapely_geometry_to_vector(
            asset_points,
            asset_points_path,
            self.wkt,
            'GeoJSON',
            fields={'category': ogr.OFTString, 'company': ogr.OFTString},
            attribute_list=[
                {'category': 'mine', 'company': 'A'},
                {'category': 'restaurant', 'company': 'A'},
                {'category': 'mine', 'company': 'B'}],
            ogr_geom_type=ogr.wkbPoint)

        asset_results_path = os.path.join(self.workspace_dir, 'asset_results.gpkg')
        company_results_path = os.path.join(self.workspace_dir, 'company_results.csv')

        namespace = argparse.Namespace()
        namespace.mode = 'points'
        namespace.ecosystem_service_table = self.es_table_path
        namespace.buffer_table = None
        namespace.asset_vector = asset_points_path
        namespace.footprint_results_path = asset_results_path
        namespace.company_results_path = company_results_path
        execute(namespace)

        actual_asset_gdf = geopandas.read_file(asset_results_path)
        expected_asset_gdf = geopandas.GeoDataFrame({
            'category': ['mine', 'restaurant', 'mine'],
            'company': ['A', 'A', 'B'],
            'es_1': [11.0, 55.0, 92.0],
            'es_1_flag': [False, False, True],
            'es_2': [numpy.nan, 2.5, numpy.nan],
            'es_2_flag': [False, False, False],
            'geometry': asset_points
        })
        pandas.testing.assert_frame_equal(actual_asset_gdf, expected_asset_gdf)

        actual_company_df = pandas.read_csv(company_results_path)
        expected_company_df = pandas.DataFrame({
            'company': ['A', 'B'],
            'es_1_sum': [66.0, 92.0],
            'es_1_assets': [2, 1],
            'es_1_flagged': [0, 1],
            'percent_es_1_flagged': [0.0, 100.0],
            'es_2_sum': [2.5, 0],
            'es_2_assets': [1, 0],
            'es_2_flagged': [0, 0],
            'percent_es_2_flagged': [0.0, 0.0],
            'total_assets': [2, 1],
            'total_flagged': [0, 1],
            'percent_total_flagged': [0.0, 100.0]
        })
        pandas.testing.assert_frame_equal(actual_company_df, expected_company_df)

    def test_complete_run_point_buffer_mode(self):
        from impact.src import execute

        self.make_es_inputs()

        asset_points_path = os.path.join(self.workspace_dir, 'assets.geojson')
        asset_points = [Point(5.55, -4.51), Point(12.9, -12.9), Point(6.09, -20.06)]
        pygeoprocessing.shapely_geometry_to_vector(
            asset_points,
            asset_points_path,
            self.wkt,
            'GeoJSON',
            fields={'category': ogr.OFTString, 'company': ogr.OFTString},
            attribute_list=[
                {'category': 'mine', 'company': 'A'},
                {'category': 'restaurant', 'company': 'A'},
                {'category': 'mine', 'company': 'B'}],
            ogr_geom_type=ogr.wkbPoint)

        buffer_table_path = os.path.join(self.workspace_dir, 'buffer_table.csv')
        pandas.DataFrame({
            'category': ['mine', 'restaurant'],
            'area': [12.5, 3]
        }).to_csv(buffer_table_path)

        asset_results_path = os.path.join(self.workspace_dir, 'asset_results.gpkg')
        company_results_path = os.path.join(self.workspace_dir, 'company_results.csv')

        namespace = argparse.Namespace()
        namespace.mode = 'points'
        namespace.ecosystem_service_table = self.es_table_path
        namespace.buffer_table = buffer_table_path
        namespace.asset_vector = asset_points_path
        namespace.footprint_results_path = asset_results_path
        namespace.company_results_path = company_results_path
        namespace.n_workers = -1
        execute(namespace)

        actual_asset_gdf = geopandas.read_file(asset_results_path)
        # centroid of the footprint should equal the original point,
        # within float precision
        for actual, expected in zip(actual_asset_gdf['geometry'].centroid, asset_points):
            self.assertTrue(actual.equals_exact(expected, tolerance=1e-6))

        # area of the footprint does not exactly equal the specified area because
        # the buffer is a many-sided regular polygon approximating a circle.
        # it seems to be accurate to within 0.5%.
        for actual, expected in zip(actual_asset_gdf['geometry'].area, [12.5, 3, 12.5]):
            numpy.testing.assert_allclose(actual, expected, rtol=5e-3, atol=0)

        actual_asset_df = pandas.DataFrame(actual_asset_gdf).drop(columns='geometry')
        expected_asset_df = pandas.DataFrame({
            'category': ['mine', 'restaurant', 'mine'],
            'company': ['A', 'A', 'B'],
            'es_1_max': [12, 55, 92],
            'es_1_count': [3, 1, 4],
            'es_1_nodata_count': [0, 0, 0],
            'es_1_mean': [8, 55.0, 86.5],
            'es_1_flag': [False, False, True],
            'es_1_adj_sum': [
                # multiply by whatever the actual geometry area is because
                # we don't know exactly what the area should be, but we already
                # asserted that it's close enough.
                val * area for val, area in zip(
                    [2, 13.75, 21.625], actual_asset_gdf['geometry'].area)],
            'es_2_max': [0.0, 2.5, numpy.nan],
            'es_2_count': [1, 1, 0],
            'es_2_nodata_count': [2, 0, 0],
            'es_2_mean': [0.0, 2.5, numpy.nan],
            'es_2_flag': [False, False, False],
            'es_2_adj_sum': [
                # multiply by whatever the actual geometry area is because
                # we don't know exactly what the area should be, but we already
                # asserted that it's close enough.
                val * area for val, area in zip(
                    [0, 0.625, numpy.nan], actual_asset_gdf['geometry'].area)]
        })
        pandas.testing.assert_frame_equal(actual_asset_df, expected_asset_df)

        actual_company_df = pandas.read_csv(company_results_path)
        expected_company_df = pandas.DataFrame({
            'company': ['A', 'B'],
            'es_1_adj_sum': [
                expected_asset_df['es_1_adj_sum'][0] + expected_asset_df['es_1_adj_sum'][1],
                expected_asset_df['es_1_adj_sum'][2]],
            'es_1_area': [
                actual_asset_gdf['geometry'].area[0] + actual_asset_gdf['geometry'].area[1],
                actual_asset_gdf['geometry'].area[2]],
            'es_1_assets': [2, 1],
            'es_1_flagged': [0, 1],
            'percent_es_1_flagged': [0.0, 100.0],
            'es_2_adj_sum': [
                0 + expected_asset_df['es_2_adj_sum'][1], 0],
            'es_2_area': [
                actual_asset_gdf['geometry'].area[0] + actual_asset_gdf['geometry'].area[1],
                0],
            'es_2_assets': [2, 0],
            'es_2_flagged': [0, 0],
            'percent_es_2_flagged': [0.0, 0.0],
            'total_area': [
                actual_asset_gdf['geometry'].area[0] + actual_asset_gdf['geometry'].area[1],
                actual_asset_gdf['geometry'].area[2]],
            'total_assets': [2, 1],
            'total_flagged': [0, 1],
            'percent_total_flagged': [0.0, 100.0]
        })
        pandas.testing.assert_frame_equal(actual_company_df, expected_company_df)


    def test_complete_run_polygon_mode(self):
        from impact.src import execute

        self.make_es_inputs()

        asset_polygons_path = os.path.join(self.workspace_dir, 'assets.geojson')
        asset_polygons = [
            Polygon([(4.6, -2.3), (7.8, -5.2), (4.6, -5.2), (4.6, -2.3)]),
            Polygon([(12.5, -12.5), (13.5, -12.5), (13.5, -13.5), (12.5, -13.5), (12.5, -12.5)]),
            Polygon([(6.01, -20.01), (6.02, -20.01), (6.01, -20.02), (6.01, -20.01)])]
        pygeoprocessing.shapely_geometry_to_vector(
            asset_polygons,
            asset_polygons_path,
            self.wkt,
            'GeoJSON',
            fields={'category': ogr.OFTString, 'company': ogr.OFTString},
            attribute_list=[
                {'category': 'mine', 'company': 'A'},
                {'category': 'restaurant', 'company': 'A'},
                {'category': 'mine', 'company': 'B'}],
            ogr_geom_type=ogr.wkbPolygon)

        buffer_table_path = os.path.join(self.workspace_dir, 'buffer_table.csv')
        pandas.DataFrame({
            'category': ['mine', 'restaurant'],
            'area': [12.5, 3]
        }).to_csv(buffer_table_path)

        asset_results_path = os.path.join(self.workspace_dir, 'asset_results.gpkg')
        company_results_path = os.path.join(self.workspace_dir, 'company_results.csv')

        namespace = argparse.Namespace()
        namespace.mode = 'polygons'
        namespace.ecosystem_service_table = self.es_table_path
        namespace.buffer_table = None
        namespace.asset_vector = asset_polygons_path
        namespace.footprint_results_path = asset_results_path
        namespace.company_results_path = company_results_path
        namespace.n_workers = -1
        execute(namespace)

        actual_asset_gdf = geopandas.read_file(asset_results_path)
        expected_asset_gdf = geopandas.GeoDataFrame({
            'category': ['mine', 'restaurant', 'mine'],
            'company': ['A', 'A', 'B'],
            'es_1_max': [12, 55, 92],
            'es_1_count': [3, 1, 1],
            'es_1_nodata_count': [0, 0, 0],
            'es_1_mean': [8.0, 55.0, 92.0],
            'es_1_flag': [False, False, True],
            'es_1_adj_sum': [9.28, 13.75, 0.00115],
            'es_2_max': [0.0, 2.5, numpy.nan],
            'es_2_count': [1, 1, 0],
            'es_2_nodata_count': [2, 0, 0],
            'es_2_mean': [0.0, 2.5, numpy.nan],
            'es_2_flag': [False, False, False],
            'es_2_adj_sum': [0, 0.625, numpy.nan],
            'geometry': asset_polygons
        })
        pandas.testing.assert_frame_equal(actual_asset_gdf, expected_asset_gdf)

        actual_company_df = pandas.read_csv(company_results_path)
        expected_company_df = pandas.DataFrame({
            'company': ['A', 'B'],
            'es_1_adj_sum': [23.03, 0.00115],
            'es_1_area': [5.64, 0.00005],
            'es_1_assets': [2, 1],
            'es_1_flagged': [0, 1],
            'percent_es_1_flagged': [0.0, 100.0],
            'es_2_adj_sum': [0.625, 0],
            'es_2_area': [5.64, 0],
            'es_2_assets': [2, 0],
            'es_2_flagged': [0, 0],
            'percent_es_2_flagged': [0.0, 0.0],
            'total_area': [5.64, 0.00005],
            'total_assets': [2, 1],
            'total_flagged': [0, 1],
            'percent_total_flagged': [0.0, 100.0]
        })
        pandas.testing.assert_frame_equal(actual_company_df, expected_company_df)
