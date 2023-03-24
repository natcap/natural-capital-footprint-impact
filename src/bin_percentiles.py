import argparse

import geopandas
import numpy
import pandas

def bin_to_percentile(footprint_path, es_path, out_path):
    """Bin footprint stats against global percentiles.

    Args:
        footprint_path (str): path to a GDAL-supported footprint polygon vector
        es_path (str): path to the ecosystem service CSV, which should
            have the following columns: es_id (the unique identifier for
            each ecosystem service); path (the path to the global ecosystem
            service raster); and the numbers 0 through 100, storing the
            integer percentile values for each ecosystem service globally.
        out_path (str): path to write out the resulting footprint vector
            with percentiles

    Returns:
        None
    """
    id_col = 'es_id'
    percentile_cols = [str(i) for i in range(101)]
    es_df = pandas.read_csv(
        es_path,
        index_col=id_col,
        usecols=[id_col, *percentile_cols],
        dtype={i: float for i in percentile_cols})
    es_percentile_dict = {
        es_id: numpy.array(row) for es_id, row in es_df.iterrows()
    }
    gdf = geopandas.read_file(footprint_path)
    for es_id, percentile_array in es_percentile_dict.items():
        valid_mask = gdf[f'{es_id}_count'] > 0
        gdf[f'mean_{es_id}_percentile'] = numpy.full(gdf.shape[0], -1)
        gdf[f'max_{es_id}_percentile'] = numpy.full(gdf.shape[0], -1)

        mean_percentile_array = numpy.full(gdf.shape[0], -1)
        max_percentile_array = numpy.full(gdf.shape[0], -1)
        es_mean = (
            gdf[valid_mask][f'{es_id}_sum'] /
            gdf[valid_mask][f'{es_id}_count'])
        mean_percentile_array[valid_mask] = numpy.digitize(
            es_mean, percentile_array)
        max_percentile_array[valid_mask] = numpy.digitize(
            gdf[valid_mask][f'{es_id}_max'], percentile_array)
        gdf[f'mean_{es_id}_percentile'] = mean_percentile_array
        gdf[f'max_{es_id}_percentile'] = max_percentile_array

    gdf.to_file(out_path, driver='GPKG', layer='footprints')
        
def main():
    # set up the command line interface
    parser = argparse.ArgumentParser()
    parser.add_argument('footprint_path')
    parser.add_argument('es_path')
    parser.add_argument('out_vector_path')
    args = parser.parse_args()
    footprint_stats(args.footprint_path, args.es_path, args.out_vector_path)
        
if __name__ == '__main__':
    main()
