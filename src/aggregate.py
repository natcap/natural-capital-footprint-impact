import argparse

import geopandas
import numpy
import pandas

def aggregate(footprint_path, out_path, aggregate_by):
    """Aggregate footprint stats up to the company level.

    Args:
        footprint_path (str): path to a GDAL-supported footprint polygon vector
        out_path (str): path to write out the CSV table of aggregated data
        aggregate_by (str): footprint attribute to aggregate by

    Returns:
        None
    """
    gdf = geopandas.read_file(footprint_path)
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
                valid_company_rows[f'mean_{es_id}_percentile'] > 90) /
                company_rows.shape[0] * 100

        # total area of asset footprints per company (overlapping data or not)
        results[company]['total_area'] = company_rows['geometry'].area.sum()
        # total number of assets per company (whether overlapping data or not)
        results[company]['total_assets'] = company_rows.shape[0]

    df = pandas.DataFrame(results).T
    for es_id in es_ids:
        for col in [f'{es_id}_assets', f'{es_id}_count_mean>90th',
                    f'{es_id}_count_max>90th', 'total_assets']:
            df[col] = df[col].astype(int)
    df.to_csv(out_path, float_format='%.5f')
        
def main():
    # set up the command line interface
    parser = argparse.ArgumentParser()
    parser.add_argument('footprint_path')
    parser.add_argument('out_path')
    parser.add_argument('--aggregate_by')
    args = parser.parse_args()
    aggregate(args.footprint_path, args.out_path, args.aggregate_by)
        
if __name__ == '__main__':
    main()
