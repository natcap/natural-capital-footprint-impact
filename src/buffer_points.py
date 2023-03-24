import argparse
import math

import geopandas
import pandas

def buffer_points(point_vector_path: str, buffer_csv_path: str, out_vector_path: str, attr: str, area_col='footprint_area'):
    """Buffer points according to a given attribute.
    
    For a given row in `gdf`, `row['geometry']` will be buffered to form a
    regular polygon approximating a circle. Its area is equal to
    `buffer_df[row[attr]]`.

    For example, suppose your attribute is called 'facility_category'. Then
    the point vector attribute table should contain a `facility_category`
    column.
    
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
        Error if there are `facility_category` values in `gdf` that are not 
            found in `buffer_df`
        Warning if there are `facility_category` values in `buffer_df` that 
            are not found in `gdf`
    """
    gdf = geopandas.read_file(point_vector_path)
    buffer_df = pandas.read_csv(buffer_csv_path)
    for _, row in buffer_df.iterrows():
        # calculate the radius needed to draw a circle that has the given area
        buffer_radius = math.sqrt(row[area_col] / math.pi)
        mask = gdf[attr] == row[attr]
        # draw a polygon that approximates a circle
        matches = gdf[mask]
        gdf.loc[mask, 'geometry'] = gdf.loc[mask, 'geometry'].buffer(buffer_radius)
    gdf.to_file(out_vector_path, driver='GPKG', layer='layer')

def main():
    # set up the command line interface
    parser = argparse.ArgumentParser()
    parser.add_argument('point_vector_path')
    parser.add_argument('buffer_csv_path')
    parser.add_argument('out_vector_path')
    args = parser.parse_args()
    buffer_points(args.point_vector_path, args.buffer_csv_path, args.out_vector_path)
        
if __name__ == '__main__':
    main()
