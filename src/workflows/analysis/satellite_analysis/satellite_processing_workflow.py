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
    SensorProcessingStrategy,
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

logger = logging.getLogger("satellite_workflow")


class SatelliteWorkflow:

    def __init__(
        self, path_config, city, satellite_type, bbox, strategy, indices, file_suffix
    ):
        self.city = city
        self.path_config = path_config
        self.satellite_download_dir = (
            path_config.sentinel_dir
            if satellite_type == "sentinel"
            else path_config.landsat_dir
        )
        self.satellite_type = satellite_type
        self.bbox = bbox
        self.strategy = strategy
        self.indices = indices
        self.file_suffix = file_suffix
        self.downloaded_date_folders = os.listdir(self.satellite_download_dir)
        self.processing_dir = self.path_config.processing
        self.result_dir = self.path_config.results

    def run(self):
        self._merge_response_tiles_and_compute_indices()
        self._compute_aggregates_from_indices()
        self._crop_by_bbox_to_result_folder()

    def _merge_response_tiles_and_compute_indices(self):
        logger.info("Merge response tiles and compute satellite indices")
        for date in self.downloaded_date_folders:
            tile_files = glob(
                os.path.join(self.satellite_download_dir, date) + "/*/*/response.tiff"
            )
            if len(tile_files) == 0:
                continue

            vrt_file = os.path.join(
                self._processing_folder_for_date_images(date),
                date + "_%s_response.vrt" % (self.satellite_type),
            )
            raster_file = vrt_file.replace(".vrt", ".tiff")

            build_vrt_from_tiles(tile_files, vrt_file)
            raster_from_vrt(vrt_file, raster_file)

            processor = SatelliteImageProcessor(raster_file)
            processor.process(self.strategy, self.indices)
            for index in self.indices:
                out_filepath = self._filepath_for_index_and_date(index, date)
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

    def _crop_by_bbox_to_result_folder(self):
        for index in self.indices:
            files_for_index = self._get_all_processed_files_for_index(index)
            for input_fp in files_for_index:
                result_filepath = input_fp.replace(self.processing_dir, self.result_dir)
                crop_geotiff_by_bbox(input_fp, self.bbox, result_filepath)
                build_pyramid(result_filepath)

    # ---------------------------------------------------------------------------------------------------- #

    def _filepath_for_index_and_date(self, index, date):
        index_timestep_dir = self._processing_folder_for_indices_timesteps(index)
        out_filepath = os.path.join(index_timestep_dir, f"{index}_{date}.tiff")
        return out_filepath

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

    def _get_all_processed_files_for_index(self, index):
        pattern = os.path.join(self._get_index_base_dir(index), "**", "*.tiff")
        files_for_index = sorted(glob(pattern, recursive=True))
        return files_for_index

    def _processing_folder_for_indices_timesteps(self, index):
        dir = os.path.join(self._get_index_base_dir(index), "timesteps")
        self._ensure_dir(dir)
        return dir

    def _processing_folder_for_indices_aggregates(self, index):
        dir = os.path.join(self._get_index_base_dir(index), "aggregates")
        self._ensure_dir(dir)
        return dir

    def _get_index_base_dir(self, index):
        category = "heat_islands" if index == "lst" else "vegetation_indices"
        index_base_dir = os.path.join(self.processing_dir, self.city, category, index)
        return index_base_dir

    def _ensure_dir(self, dir):
        if not os.path.exists(dir):
            os.makedirs(dir)


class VegetationIndicesProcessingWorkflow(SatelliteWorkflow):

    def __init__(self, path_config, city, bbox):
        strategy = SentinelProcessor(S2_EVALSCRIPT_FILE)
        indices = [strategy.NDVI, strategy.NDMI]
        super(VegetationIndicesProcessingWorkflow, self).__init__(
            path_config,
            city,
            "sentinel",
            bbox,
            strategy,
            indices,
            file_suffix="/*sentinel_response.tiff",
        )


class LandSurfaceTemperaturProcessingWorkflow(SatelliteWorkflow):

    def __init__(self, path_config, city, bbox):

        strategy = LandsatProcessor(L8_EVALSCRIPT_FILE)
        super(LandSurfaceTemperaturProcessingWorkflow, self).__init__(
            path_config,
            city,
            "landsat",
            bbox,
            strategy,
            indices=[strategy.LST],
            file_suffix="/*landsat_response.tiff",
        )
