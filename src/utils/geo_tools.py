# Copyright (c) 2025 Vision Impulse GmbH
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Authors: Benjamin Bischke

import subprocess
import tempfile
import os
import geopandas as gpd
import pandas as pd
import rasterio
import pyproj
import osmnx as ox
import logging

from rasterio.windows import from_bounds
from shapely.geometry import box
from rasterio.warp import transform_bounds
from typing import Tuple
from pyproj import CRS
from shapely.ops import unary_union
from osmnx._errors import InsufficientResponseError
from shapely.geometry import MultiPolygon

logger = logging.getLogger("utils")


def get_utm_crs(geometry):
    lon = geometry.centroid.x
    zone_number = int((lon + 180) / 6) + 1
    return CRS.from_epsg(32600 + zone_number)  # for northern hemisphere


def get_aoi_bbox_by_city_name(city_name, buffer_m):
    try:
        gdf = ox.geocode_to_gdf(f"{city_name}, Germany")
    except InsufficientResponseError:
        logger.error(
            f"No result found for the given city name {city_name}. Ensure that there is no typo in the provided city name. If the city name can still not be resolved, please provide a bounding box for the area of interest in the EPSG:4326. projection"
        )
        exit(0)

    # Extract polygon in local zone
    gdf_local = gdf.to_crs(get_utm_crs(gdf.geometry[0]))
    geometry_local = gdf_local.loc[0, "geometry"]
    polygon_local = geometry_local.buffer(buffer_m)

    # Buffered bounds in 4326
    buffered = gpd.GeoDataFrame(geometry=[polygon_local], crs=gdf_local.crs).to_crs(
        epsg=4326
    )
    bounds = buffered.total_bounds  # [minx, miny, maxx, maxy]

    return bounds.tolist()


def build_pyramid(output_file):
    cmd = "gdaladdo -r cubic %s 2 4 8 16 32" % (output_file)
    p = subprocess.Popen(cmd, shell=True)
    p.wait()


def crop_geotiff_by_bbox(
    input_path: str, bbox_4326: Tuple[float, float, float, float], output_path: str
):
    """
    Crop a GeoTIFF file to the given bounding box (in EPSG:4326) and save it.

    Parameters:
    - input_path: str, path to the input GeoTIFF file
    - bbox_4326: tuple of (minx, miny, maxx, maxy) in EPSG:4326
    - output_path: str, path to save the cropped GeoTIFF
    """
    with rasterio.open(input_path) as src:
        dst_crs = src.crs

        transformed_bbox = transform_bounds("EPSG:4326", dst_crs, *bbox_4326)
        window = from_bounds(*transformed_bbox, transform=src.transform)
        transform = src.window_transform(window)
        data = src.read(window=window)

        out_meta = src.meta.copy()
        out_meta.update(
            {"height": data.shape[1], "width": data.shape[2], "transform": transform}
        )
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(data)

    logger.debug(f"Cropped GeoTIFF saved to: {output_path}")


def crop_gpkg_by_bbox(
    input_path: str,
    layer: str,
    output_folder: str,
    bbox: tuple,
    output_filename: str = "cropped.gpkg",
):
    """
    Crop a GPKG file to the given bounding box and save the result.

    Parameters:
    - input_path: str, path to the input .gpkg file
    - layer: str, name of the layer inside the GPKG to read
    - output_folder: str, path to save the cropped file
    - bbox: tuple of (minx, miny, maxx, maxy)
    - output_filename: str, name of the cropped output file
    """
    minx, miny, maxx, maxy = bbox
    bounding_box = box(minx, miny, maxx, maxy)

    gdf = gpd.read_file(input_path, layer=layer)
    cropped_gdf = gdf[gdf.geometry.intersects(bounding_box)]

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, output_filename)

    cropped_gdf.to_file(output_path, layer=layer, driver="GPKG")
    logger.debug(f"Cropped GPKG saved to: {output_path}")


def build_vrt_from_tiles(tile_paths, vrt_file, src_nodata=0, vrt_nodata=0) -> None:
    if os.path.exists(vrt_file):
        return

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tf:
        for path in tile_paths:
            tf.write(f"{path}\n")
        tile_list_file = tf.name

    try:
        cmd = [
            "gdalbuildvrt",
            "-input_file_list",
            tile_list_file,
            "-srcnodata",
            str(src_nodata),
            "-vrtnodata",
            str(vrt_nodata),
            vrt_file,
        ]
        subprocess.run(cmd, check=True)
        logger.debug(f"VRT created: {vrt_file}")
    finally:
        os.remove(tile_list_file)


def raster_from_vrt(vrt_file, output_file):
    if os.path.exists(output_file):
        return

    try:
        cmd = [
            "gdal_translate",
            str(vrt_file),
            str(output_file),
            "-co",
            "TILED=YES",
        ]
        subprocess.run(cmd, check=True)
        logger.debug(f"GeoTIFF created: {output_file}")
    finally:
        pass


def merge_geopackages(input_gpkg_files, output_gpkg_path, unify_polygons=False):
    """
    Merges multiple GeoPackage (.gpkg) files into a single GeoPackage file.

    Args:
        input_gpkg_files (list): A list of paths to the input GeoPackage files.
        output_gpkg_path (str): The path where the merged GeoPackage will be saved.
    """

    if not input_gpkg_files:
        logger.debug("No input GeoPackage files provided for merging.")
        return

    gdf_list = []
    for i, gpkg_file in enumerate(input_gpkg_files):
        logger.debug(f"Reading file {i+1}/{len(input_gpkg_files)}: {gpkg_file}")
        try:
            gdf = gpd.read_file(gpkg_file).to_crs("EPSG:4326")
            gdf_list.append(gdf)
        except Exception as e:
            logger.error(f"Warning: Skipping {gpkg_file}. Error: {e}")

    logger.info("Merging all GeoDataFrames...")
    if unify_polygons:
        flattened_polys = []
        for gdf in gdf_list:
            for geom in gdf.geometry:
                if geom.geom_type == "Polygon":
                    flattened_polys.append(geom)
                elif geom.geom_type == "MultiPolygon":
                    flattened_polys.extend(geom.geoms)  # Unpack each sub-polygon
                else:
                    logger.debug(f"Skipping geometry type: {geom.geom_type}")

        # Create one MultiPolygon from all valid Polygons
        merged_geom = MultiPolygon(flattened_polys)
        merged_gdf = gpd.GeoDataFrame(geometry=[merged_geom], crs=gdf_list[0].crs)
    else:
        merged_gdf = gpd.GeoDataFrame(
            pd.concat(gdf_list, ignore_index=True), crs=gdf_list[0].crs
        )

    # Save the merged GeoDataFrame to the output GeoPackage
    logger.debug(f"Saving merged data to {output_gpkg_path}")
    merged_gdf.to_file(output_gpkg_path, driver="GPKG")
