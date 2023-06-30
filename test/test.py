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

def make_simple_shp(base_shp_path, origin):
    """Make a 100x100 ogr rectangular geometry shapefile.

    Args:
        base_shp_path (str): path to the shapefile.

    Returns:
        None.

    """
    # Create a new shapefile
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.CreateDataSource(base_shp_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(26910)  # Spatial reference UTM Zone 10N
    layer = data_source.CreateLayer('layer', srs, ogr.wkbPolygon)

    # Add an FID field to the layer
    field_name = 'FID'
    field = ogr.FieldDefn(field_name)
    layer.CreateField(field)

    # Create a rectangular geometry
    lon, lat = origin[0], origin[1]
    width = 100
    rect = ogr.Geometry(ogr.wkbLinearRing)
    rect.AddPoint(lon, lat)
    rect.AddPoint(lon + width, lat)
    rect.AddPoint(lon + width, lat - width)
    rect.AddPoint(lon, lat - width)
    rect.AddPoint(lon, lat)

    # Create the feature from the geometry
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(poly)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField(field_name, '1')
    feature.SetGeometry(poly)
    layer.CreateFeature(feature)

    feature = None
    data_source = None


def make_raster_from_array(base_array, base_raster_path):
    """Make a raster from an array on a designated path.

    Args:
        array (numpy.ndarray): the 2D array for making the raster.
        raster_path (str): path to the raster to be created.

    Returns:
        None.

    """
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(26910)  # UTM Zone 10N

    project_wkt = srs.ExportToWkt()

    # Each pixel is 1x1 m
    pygeoprocessing.numpy_array_to_raster(
        base_array, -1, (1, -1), (1180000, 690000), project_wkt,
        base_raster_path)


def make_es_raster(path):
    """Make a 100x100 LULC raster with two LULC codes on the raster path.

    Args:
        lulc_raster_path (str): path to the LULC raster.

    Returns:
        None.
    """
    size = 100
    lulc_array = numpy.ones((size, size), dtype=numpy.int16)
    lulc_array[size // 2:, :] = 20
    print(lulc_array)
    make_raster_from_array(lulc_array, path)
    print(pygeoprocessing.get_raster_info(path))


class FootprintImpactWorkflowTests(unittest.TestCase):
    """Tests for the Carbon Model ARGS_SPEC and validation."""

    def setUp(self):
        """Create a temporary workspace."""
        self.workspace_dir = tempfile.mkdtemp()
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32731)  # WGS84/UTM zone 31s
        self.wkt = srs.ExportToWkt()
        self.es_1_path = '/Users/emily/Documents/es_1.tif'#os.path.join(self.workspace_dir, 'es_1.tif')
        self.es_2_path = '/Users/emily/Documents/es_2.tif'#os.path.join(self.workspace_dir, 'es_1.tif')

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

        asset_results_path = '/Users/emily/Documents/asresults.gpkg'#os.path.join(self.workspace_dir, 'asset_results.gpkg')
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

        asset_results_path = '/Users/emily/Documents/asresults.gpkg'#os.path.join(self.workspace_dir, 'asset_results.gpkg')
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

    def test_buffer_points(self):
        from impact.src import buffer_points
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
            point = Point([(1180050, 690050)])
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
                category,area
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


    @mock.patch('rasterio.DatasetReader.sample')
    def test_point_stats(self, mock_rasterio_sample):
        from impact.src import point_stats

        asset_path = os.path.join(self.workspace_dir, 'assets.gpkg')
        schema = {
            'geometry': 'Point',
            'properties': {
                'id': 'int',
                'category': 'str'
            }
        }
        with fiona.open(asset_path, 'w', 'GPKG', schema=schema, crs=from_epsg(8857)) as out:
            point = Point([0, 0])
            out.write({
              'geometry': mapping(point),
              'properties': {
                  'id': 1,
                  'category': 'x'
              }
            })

        pygeoprocessing.numpy_array_to_raster(
            numpy.array([
                [0, 1, 2],
                [3, 4, 5],
                [6, 7, 8]]),
            'service.tif')

        with open(es_table_path, 'w') as table:
            table.write(textwrap.dedent(
                """
                es_id,es_value_path,flag_threshold
                foo,foo.tif,15
                """))

        point_stats(point_path, es_table_path, id_col)

    def test_footprint_stats(self):
        from impact.src import footprint_stats

        footprint_path = os.path.join(self.workspace_dir, 'assets.gpkg')
        es_table_path = os.path.join(self.workspace_dir, 'services.csv')
        out_path = os.path.join(self.workspace_dir, 'out.gpkg')
        # schema = {
        #     'geometry': 'Polygon',
        #     'properties': {
        #         'id': 'int',
        #         'foo_category': 'str'
        #     }
        # }
        # polygon = Polygon([
        #     [1180000, 690000],
        #     [1180050, 690000],
        #     [1180000, 690050],
        #     [1180000, 690000]])
        # with fiona.open(footprint_path, 'w', 'GPKG', schema=schema, crs=from_epsg(26910)) as out:
        #     out.write({
        #       'geometry': mapping(polygon),
        #       'properties': {
        #           'id': 1,
        #           'foo_category': 'x'
        #       }
        #     })
        make_simple_shp(footprint_path, (1180000.0, 690000.0))
        es_path = os.path.join(self.workspace_dir, 'foo.tif')
        make_es_raster(es_path)
        with open(es_table_path, 'w') as table:
            table.write(textwrap.dedent(
                f"""
                es_id,es_value_path,flag_threshold
                foo,{es_path},15
                """))
        footprint_gdf = footprint_stats(footprint_path, es_table_path)
        print(footprint_gdf)

        expected_gdf = geopandas.GeoDataFrame(
            {
                'fid': [1],
                'id': [1],
                'foo_category': ['x'],
                # 'geometry': [polygon],
                'foo_max': [16],
                'foo_sum': [45],
                'foo_count': [8],
                'foo_nodata_count': [0],
                'foo_flag': [True]
            }
        , crs='EPSG:8857')
        expected_gdf = expected_gdf.set_index('fid')
        geopandas.testing.assert_geodataframe_equal(footprint_gdf, expected_gdf)

    def test_aggregate_footprints(self):
        pass

    def test_aggregate_points(self):
        pass

    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_cli_point_mode_no_buffer(self, mock_parse_args):
        from impact.cli import main

        namespace = argparse.Namespace()
        namespace.mode = 'points'
        namespace.buffer_table = None
        namespace.ecosystem_service_table = None
        namespace.asset_vector = None
        namespace.footprint_results_path = None
        namespace.company_results_path = None
        mock_parse_args.return_value = namespace

        main()

        # point stats gpkg exists and is correct
        # company stats csv exists and is correct

    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_cli_point_mode_with_buffer(self, mock_parse_args):
        from impact.cli import main

        namespace = argparse.Namespace()
        namespace.mode = 'points'
        namespace.buffer_table = ''
        namespace.ecosystem_service_table = ''
        mock_parse_args.return_value = namespace

        main()

        # footprint stats gpkg exists and is correct
        # company stats csv exists and is correct

    @mock.patch('pygeoprocessing.zonal_statistics')
    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_cli_polygon_mode(self, mock_parse_args, mock_zonal_statistics):
        from impact.cli import main

        mock_zonal_statistics.return_value = {1: {
            'sum': 45, 'count': 8, 'min': 0, 'max': 16, 'nodata_count': 0}}

        namespace = argparse.Namespace()
        namespace.mode = 'polygons'
        percentile_table_path = os.path.join(self.workspace_dir, 'services.csv')
        footprint_path = os.path.join(self.workspace_dir, 'assets.gpkg')
        namespace.ecosystem_service_table = percentile_table_path
        namespace.asset_vector = footprint_path
        mock_parse_args.return_value = namespace

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
                es_id,es_value_path,flag_threshold
                foo,foo.tif,40
                """))



        main()

        # footprint stats gpkg exists and is correct
        # company stats csv exists and is correct

