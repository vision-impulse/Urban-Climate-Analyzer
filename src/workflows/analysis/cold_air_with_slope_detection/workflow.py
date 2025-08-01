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

import glob
import os
from enum import Enum
from typing import Any, Union
from urllib.parse import urljoin

import pandas as pd
import utils.date_utils as util
import geopandas as gpd
import pyproj
import shutil
import numpy as np
import rasterio
import logging

from shapely.geometry import box
from shapely.ops import unary_union
from workflows.workflow_base import BaseWorkflow
from workflows.analysis.cold_air_detection.workflow import ColdAirZoneWorkflow
from workflows.analysis.topo_slope.workflow import SlopeExtractionWorkflow

from utils.geo_tools import (
    merge_geopackages,
)
from multiprocessing import Pool, cpu_count
from rasterio.mask import mask as rio_mask
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union

from rasterio.errors import RasterioError
from shapely.geometry import box

logger = logging.getLogger("cold_air_with_slope_workflow")


class ColdAirZoneWithSlopeWorkflow(BaseWorkflow):

    RESULT_FILENAME = "cold_air_zones_with_slope.gpkg"

    def __init__(
        self,
        path_config,
        city,
        bbox,
        dataset_url_dgl,
        dataset_url_clc,
        dem_folder,
        override_files,
        dem_scale_factor,
    ):
        super(ColdAirZoneWithSlopeWorkflow, self).__init__(
            city, bbox, "cold_air_zones_with_slope"
        )
        self.city = city
        self.path_config = path_config
        self.processing_dir = path_config.processing
        self.results_dir = path_config.results
        self.dataset_url_dgl = dataset_url_dgl
        self.dataset_url_clc = dataset_url_clc
        self.dem_folder = dem_folder
        self.override_files = override_files
        self.dem_scale_factor = dem_scale_factor
        self.slope_degree_threshold = 2.0
        self.slope_simplify_tolerance = 0
        self.slope_min_area = 1
        self.dem_foldername = os.path.basename(self.dem_folder)
        self.wflow_name = "cold_air_zones_with_slope"

        self.process_wflow_folder = os.path.join(
            self.processing_dir,
            self.city,
            self.wflow_name
        )

        # input from slope workflow
        self.slope_raster_file_dir = os.path.join(
            self.processing_dir,
            self.city,
            "slope",
            self.dem_foldername,
            "single_raster_files",
        )
        # input from cold-air workflow
        self.cold_air_mask_file = os.path.join(
            self.results_dir, self.city, "cold_air_zones", "cold_air_zones.gpkg"
        )
        # temp processing folders
        self.slope_vector_files_dir = os.path.join(
            self.processing_dir,
            self.city,
            self.wflow_name,
            self.dem_foldername,
            "single_vector_files",
        )
        self.merged_vector_files_dir = os.path.join(
            self.processing_dir,
            self.city,
            self.wflow_name,
            self.dem_foldername,
            "merged_files",
        )
        if self.override_files:
            self._remove_dir(self.process_wflow_folder)
            self._ensure_dir(self.process_wflow_folder)
        self._ensure_dir(self.slope_vector_files_dir)
        self._ensure_dir(self.merged_vector_files_dir)

        # Load vector mask
        self.mask_gdf = gpd.read_file(self.cold_air_mask_file)
        if self.mask_gdf.empty:
            logger.info("Mask cold air zones GPKG contains no geometries.")
            return

    def run(self):
        workflow_air_zone_analysis = ColdAirZoneWorkflow(
            self.path_config,
            self.city,
            self.bbox,
            self.dataset_url_dgl,
            self.dataset_url_clc,
            self.override_files,
        )
        workflow_air_zone_analysis.run()
        workflow_slope_analysis = SlopeExtractionWorkflow(
            self.path_config,
            self.city,
            self.bbox,
            self.dem_folder,
            self.override_files,
            dem_scale_factor=self.dem_scale_factor,
        )
        workflow_slope_analysis.run()
        self._extract_slope_mask_for_files()
        self._merge_vector_files_for_dataset()

    # -------------------------------------------------------------------------------------------------------#
    def _extract_slope_mask_for_files(self):
        logger.info(
            "Extracting vector slope masks with %s processes...", self.num_processes
        )
        raster_files = glob.glob(f"{self.slope_raster_file_dir}/*.slope.tif")
        tasks = [
            (
                fn,
                os.path.join(
                    self.slope_vector_files_dir,
                    os.path.basename(fn).replace(".tif", ".gpkg"),
                ),
            )
            for fn in raster_files
        ]
        with Pool(self.num_processes) as pool:
            pool.map(self._create_slope_mask_gpkg_mp, tasks)

    def _merge_vector_files_for_dataset(self):
        logger.info("Merging vector files ...")
        slope_files = glob.glob(f"{self.slope_vector_files_dir}/*slope.gpkg")
        processing_output_gpkg = os.path.join(
            self.merged_vector_files_dir, "cold_air_zones_with_slope.gpkg"
        )
        merge_geopackages(slope_files, processing_output_gpkg, unify_polygons=False)
        dst_path = os.path.join(
            self.results_dir,
            self.city,
            self.wflow_name,
            "cold_air_zones_with_slope.gpkg",
        )
        result_wflow_dir = os.path.join(self.results_dir, self.city, self.wflow_name)
        if not os.path.exists(result_wflow_dir):
            os.makedirs(result_wflow_dir)
        shutil.copyfile(processing_output_gpkg, dst_path)

    def _create_slope_mask_gpkg_mp(self, args):
        """
        Processes the raster to extract slope mask within a polygon region:
        - Reads raster and vector mask (polygon)
        - Reprojects vector to raster CRS
        - Masks the raster using the polygon geometry
        - Applies threshold, extracts slope polygons, saves to GPKG

        Parameters:
        - args: tuple of (raster_path, output_path, mask_gpkg_path)
        """
        raster_path, output_path = args
        if os.path.exists(output_path):
            return

        with rasterio.open(raster_path) as src:
            raster_crs = src.crs
            raster_transform = src.transform
            raster_nodata = src.nodata

            _mask_gdf = self.mask_gdf.to_crs(raster_crs)

            mask_geoms = [
                geom
                for geom in _mask_gdf.geometry
                if geom.is_valid and not geom.is_empty
            ]
            if not mask_geoms:
                logger.debug("No valid geometries found in mask (%s).", raster_path)
                return

            # Check if any geometry intersects with raster bounds
            raster_bounds = box(*src.bounds)
            intersection_found = any(
                geom.intersects(raster_bounds) for geom in mask_geoms
            )

            if not intersection_found:
                logger.debug(
                    "Mask geometries do not overlap raster extent (%s).", raster_path
                )
                return

            try:
                data, transform = rio_mask(src, mask_geoms, crop=True)
            except ValueError as ve:
                logger.error("Masking failed for (%s): %s", raster_path, ve)
                return
            except RasterioError as re:
                logger.error(
                    "Rasterio error during masking for (%s): %s", raster_path, re
                )
                return

            data = data[0]  # First band

            # Mask nodata
            if raster_nodata is not None:
                data_masked = np.ma.masked_equal(data, raster_nodata)
            else:
                data_masked = np.ma.masked_invalid(data)

            # Threshold mask
            threshold_mask = (data_masked > self.slope_degree_threshold).filled(False)
            if not np.any(threshold_mask):
                logger.error(
                    "No slope values above threshold in masked area for (%s).",
                    raster_path,
                )
                return

            binary_data = threshold_mask.astype(np.uint8)
            shapes_gen = shapes(binary_data, mask=threshold_mask, transform=transform)

            polygons = []
            for geom, val in shapes_gen:
                if val == 1:
                    poly = shape(geom)
                    if poly.area > 100:
                        polygons.append(poly)

            if not polygons:
                logger.error("No valid polygons after filtering for (%s).", raster_path)
                return

            merged_geom = unary_union(polygons)

            # Save as GeoDataFrame in EPSG:4326
            gdf = gpd.GeoDataFrame(geometry=[merged_geom], crs=raster_crs).to_crs(
                "EPSG:4326"
            )
            gdf["geometry"] = gdf["geometry"].simplify(0.0001, preserve_topology=True)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            gdf.to_file(output_path, driver="GPKG")
            logger.debug("Saved %s polygons to %s.", len(gdf), output_path)
