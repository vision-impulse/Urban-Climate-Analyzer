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

import os
import rasterio
import numpy as np
import logging

from workflows.analysis.satellite_analysis.satellite_processor import (
    SatelliteImageProcessor,
    SentinelProcessor,
    LandsatProcessor,
)
from glob import glob
from utils.geo_tools import (
    build_vrt_from_tiles,
    raster_from_vrt,
    crop_geotiff_by_bbox,
    build_pyramid,
)
from config.path_config import S2_EVALSCRIPT_FILE, L8_EVALSCRIPT_FILE
from collections import defaultdict
from datetime import datetime
from rasterio.enums import Resampling
from workflows.workflow_base import BaseWorkflow

logger = logging.getLogger("satellite_workflow")


class SatelliteWorkflow(BaseWorkflow):

    def __init__(
        self,
        path_config,
        city,
        bbox,
        override_files,
        workflow_name,
        satellite_type,
        satellite_download_dir,
        satellite_processing_strategy,
        indices,
    ):
        super(SatelliteWorkflow, self).__init__(
            city, path_config, bbox, override_files, workflow_name
        )
        self.satellite_type = satellite_type
        self.satellite_download_dir = satellite_download_dir
        self.strategy = satellite_processing_strategy
        self.indices = indices

        # Cleanup behavior for intermediate processing files:
        #
        # 1. If `override_files == True`, the base class will remove the entire workflow's processing folder.
        #
        # 2. The satellite image folder is never deleted, because it contains the raw input data,
        #    which should remain unchanged across runs.
        #
        # 3. The "aggregates" subfolder is always deleted, because aggregation results depend on
        #    the date and can potentially change with each new run (e.g. daily scheduled runs).
        #
        # Remove each "aggregates" subfolder for the specified indices.
        for index in self.indices:
            index_sub_folder = self._processing_folder_for_indices_aggregates(index)
            self._remove_dir(index_sub_folder)

    def run(self):
        self._merge_raw_satellite_tiles_and_compute_indices()
        self._compute_aggregates_from_indices()
        self._crop_by_bbox_and_save_in_result_folder()

    def _merge_raw_satellite_tiles_and_compute_indices(self):
        logger.info("Merge response tiles and compute satellite indices")
        for date_dir in os.listdir(self.satellite_download_dir):
            tile_files = glob(
                os.path.join(self.satellite_download_dir, date_dir)
                + "/*/*/response.tiff"
            )
            if len(tile_files) == 0:
                continue

            vrt_file = os.path.join(
                self._processing_folder_for_date_images(date_dir),
                date_dir + "_%s_response.vrt" % (self.satellite_type),
            )
            raster_file = vrt_file.replace(".vrt", ".tiff")

            build_vrt_from_tiles(tile_files, vrt_file)
            raster_from_vrt(vrt_file, raster_file)

            processor = SatelliteImageProcessor(raster_file)
            processor.process(self.strategy, self.indices)
            for index in self.indices:
                out_filepath = self._filepath_for_index_and_date(index, date_dir)
                processor.save_index_result_to_file(index, out_filepath)

    def _compute_aggregates_from_indices(
        self, agg_levels: list = ["yearly", "monthly"]
    ):
        for index in self.indices:
            timesteps_dir = self._processing_folder_for_indices_timesteps(index)
            aggregates_dir = self._processing_folder_for_indices_aggregates(index)

            grouped_files = defaultdict(list)
            for date_file in os.listdir(timesteps_dir):
                if date_file.startswith("."):
                    continue

                date_file_path = os.path.join(timesteps_dir, date_file)
                date = date_file.replace(f"{index}_", "").replace(".tiff", "")

                date = datetime.strptime(date, "%Y-%m-%d")
                if "yearly" in agg_levels:
                    grouped_files[f"year_{date.year}"].append(date_file_path)
                if "monthly" in agg_levels:
                    key = f"month_{date.year}_{date.month:02d}"
                    grouped_files[key].append(date_file_path)

            for key, paths in grouped_files.items():
                logger.info(
                    "Compute aggregations, processing %s with %s files...",
                    key,
                    len(paths),
                )
                arrays = []
                meta = None
                for path in paths:
                    with rasterio.open(path) as src:
                        arr = src.read(1, masked=True)
                        if meta is None:
                            meta = src.meta.copy()
                        arrays.append(arr)
                stacked = np.ma.stack(arrays)
                mean_arr = np.ma.mean(stacked, axis=0).filled(meta["nodata"] or -9999)
                meta.update(dtype="float32", count=1)
                meta["nodata"] = -9999

                # 3. Save result
                if "year_" in key:
                    subfolder = os.path.join(aggregates_dir, "yearly")
                    os.makedirs(subfolder, exist_ok=True)
                    out_path = os.path.join(subfolder, f"{index}_{key}.tiff")
                elif "month_" in key:
                    year, month = key.split("_")[1:]
                    subfolder = os.path.join(aggregates_dir, "monthly")
                    os.makedirs(subfolder, exist_ok=True)
                    out_path = os.path.join(subfolder, f"{index}_{key}.tiff")
                else:
                    continue

                with rasterio.open(out_path, "w", **meta) as dst:
                    dst.write(mean_arr.astype("float32"), 1)

    def _crop_by_bbox_and_save_in_result_folder(self):
        for index in self.indices:
            files_for_index = self._get_all_processed_files_for_index(index)
            for input_fp in files_for_index:
                result_filepath = input_fp.replace(self.processing_dir, self.results_dir)
                crop_geotiff_by_bbox(input_fp, self.bbox, result_filepath)
                build_pyramid(result_filepath)

    # ---------------------------------------------------------------------------------------------------- #

    def _filepath_for_index_and_date(self, index, date):
        index_timestep_dir = self._processing_folder_for_indices_timesteps(index)
        out_filepath = os.path.join(index_timestep_dir, f"{index}_{date}.tiff")
        return out_filepath

    def _get_all_processed_files_for_index(self, index):
        pattern = os.path.join(self._get_index_base_dir(index), "**", "*.tiff")
        files_for_index = sorted(glob(pattern, recursive=True))
        return files_for_index

    def _processing_folder_for_date_images(self, date_folder):
        dir = os.path.join(
            self.processing_dir,
            self.city,
            "satellite_images",
            self.satellite_type,
            date_folder,
        )
        self._ensure_dir(dir)
        return dir

    def _processing_folder_for_indices_timesteps(self, index):
        dir = os.path.join(self._get_index_base_dir(index), "timesteps")
        self._ensure_dir(dir)
        return dir

    def _processing_folder_for_indices_aggregates(self, index):
        dir = os.path.join(self._get_index_base_dir(index), "aggregates")
        self._ensure_dir(dir)
        return dir

    def _get_index_base_dir(self, index):
        return os.path.join(self.processing_workflow_dir, index)


class VegetationIndicesProcessingWorkflow(SatelliteWorkflow):

    def __init__(self, path_config, city, bbox, override_files):
        strategy = SentinelProcessor(S2_EVALSCRIPT_FILE)
        indices = [strategy.NDVI, strategy.NDMI]
        workflow_name = "vegetation_indices"
        satellite_type = "sentinel"
        super(VegetationIndicesProcessingWorkflow, self).__init__(
            path_config,
            city,
            bbox,
            override_files,
            workflow_name,
            satellite_type,
            path_config.sentinel_dir,
            strategy,
            indices
        )


class LandSurfaceTemperaturProcessingWorkflow(SatelliteWorkflow):

    def __init__(self, path_config, city, bbox, override_files):
        strategy = LandsatProcessor(L8_EVALSCRIPT_FILE)
        indices = [strategy.LST]
        workflow_name = "heat_islands"
        satellite_type = "landsat"
        super(LandSurfaceTemperaturProcessingWorkflow, self).__init__(
            path_config,
            city,
            bbox,
            override_files,
            workflow_name,
            satellite_type,
            path_config.landsat_dir,
            strategy,
            indices
        )
