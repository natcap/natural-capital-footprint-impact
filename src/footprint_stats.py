import argparse
import os

import geopandas
from osgeo import gdal, ogr
import pandas
import pygeoprocessing


def footprint_stats(footprint_path, es_table_path, out_path, id_col='es_id'):
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
    # make a copy of the input vector at the output location
    footprint_vector = ogr.Open(footprint_path)
    driver = ogr.GetDriverByName('GPKG')
    driver.CopyDataSource(footprint_vector, out_path)
    footprint_vector = None

    out_vector = gdal.OpenEx(out_path, gdal.OF_UPDATE)
    out_layer = out_vector.GetLayer()
    
    es_df = pandas.read_csv(es_table_path)
    es_raster_dict = {row[id_col]: row['path'] for _, row in es_df.iterrows()}

    stats = ['min', 'max', 'sum', 'count', 'nodata_count']
    for es_id, es_raster_path in es_raster_dict.items():
        es_raster_path = os.path.abspath(
            os.path.join(os.path.dirname(es_table_path), es_raster_path))
        zonal_stats = pygeoprocessing.zonal_statistics(
            (es_raster_path, 1), footprint_path)

        for stat in stats:
            field = ogr.FieldDefn(f'{es_id}_{stat}', ogr.OFTReal)
            field.SetWidth(24)
            field.SetPrecision(11)
            out_layer.CreateField(field)

        out_layer.ResetReading()
        out_layer.StartTransaction()

        for poly_feat in out_layer:
            poly_fid = poly_feat.GetFID()
            for stat in stats:
                if zonal_stats[poly_fid][stat] is None:
                    poly_feat.SetField(f'{es_id}_{stat}', None)
                else:
                    poly_feat.SetField(
                        f'{es_id}_{stat}', float(zonal_stats[poly_fid][stat]))
            out_layer.SetFeature(poly_feat)
        out_layer.CommitTransaction()
    out_layer, out_vector = None, None

def main():
    # set up the command line interface
    parser = argparse.ArgumentParser()
    parser.add_argument('footprint_path')
    parser.add_argument('es_path')
    parser.add_argument('out_path')
    args = parser.parse_args()
    footprint_stats(args.footprint_path, args.es_path, args.out_path)
        
if __name__ == '__main__':
    main()
