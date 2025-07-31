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
import glob
import logging

from multiprocessing import Pool, cpu_count

from workflows.workflow_base import BaseWorkflow
from workflows.analysis.topo_flow_direction.flow_direction import (
    D8FlowDirectionExtractor,
)
from utils import geo_tools as gt

logger = logging.getLogger("flow_direction_workflow")


class FlowDirectionWorkflow(BaseWorkflow):

    LAYER_NAME = "direction"

    def __init__(
        self,
        path_config,
        city,
        bbox,
        dem_folder,
        dem_scale_factor,
        gsd_grids_in_meter=None,
    ):
        super(FlowDirectionWorkflow, self).__init__(city, bbox, "flow_direction")
        logger.info("Processing DEM folder %s", dem_folder)
        self.path_config = path_config
        self.city = city
        self.dem_scale_factor = dem_scale_factor
        self.gsd_grids_in_meter = gsd_grids_in_meter or [50, 100]
        self.num_processes = cpu_count()
        self.dem_folder = dem_folder
        self.dem_filename = os.path.basename(self.dem_folder)
        self.processing_folder = path_config.processing
        self.wflow_name = "flow_direction"

        # Result dir
        self.result_dir = os.path.join(path_config.results, self.city, self.wflow_name)
        self._ensure_dir(self.result_dir)

        # Temp dirs for local processing
        self.processing_raster_dir = os.path.join(
            self.processing_folder,
            self.city,
            self.wflow_name,
            self.dem_filename,
            "single_raster_files",
        )
        self.processing_vector_dir = os.path.join(
            self.processing_folder,
            self.city,
            self.wflow_name,
            self.dem_filename,
            "single_vector_files",
        )
        self.processing_merge_dir = os.path.join(
            self.processing_folder,
            self.city,
            self.wflow_name,
            self.dem_filename,
            "merged_files",
        )
        self._ensure_dir(self.processing_raster_dir)
        self._ensure_dir(self.processing_vector_dir)
        self._ensure_dir(self.processing_merge_dir)

    def run(self):
        self._extract_flow_direction_for_dem_files()
        self._aggregate_raster_directions_to_vector_grid()
        self._merge_vector_files_for_dataset()
        self._crop_by_bbox_and_copy_gpkg()

    def _extract_flow_direction_for_dem_files(self):
        logger.info(
            "Computing flow directions with %s processes...", self.num_processes
        )

        files = glob.glob(f"{self.dem_folder}/*.tif")
        tasks = [
            (
                fn,
                os.path.join(
                    self.processing_raster_dir,
                    os.path.basename(fn).replace(".tif", ".flow_direction.tif"),
                ),
            )
            for fn in files
        ]
        with Pool(self.num_processes) as pool:
            pool.map(self._process_d8_flow_direction, tasks)

    def _aggregate_raster_directions_to_vector_grid(self):
        logger.info(
            "Aggregating raster to vector files with %s processes...",
            self.num_processes,
        )

        raster_files = glob.glob(f"{self.processing_raster_dir}/*.flow_direction.tif")
        tasks = [
            (
                fn,
                gsd,
                os.path.join(
                    self.processing_vector_dir,
                    os.path.basename(fn).replace(".tif", f"_{gsd}.gpkg"),
                ),
            )
            for fn in raster_files
            for gsd in self.gsd_grids_in_meter
        ]
        with Pool(self.num_processes) as pool:
            pool.map(self._process_d8_aggregation_to_vector, tasks)

    def _merge_vector_files_for_dataset(self):
        for gsd in self.gsd_grids_in_meter:
            flow_files = glob.glob(f"{self.processing_vector_dir}/*_{gsd}.gpkg")
            output_gpkg_fp = os.path.join(
                self.processing_merge_dir, f"flow_direction_{gsd}.gpkg"
            )
            logger.info("Merging files for grid size %s ...", gsd)
            gt.merge_geopackages(flow_files, output_gpkg_fp)

    def _crop_by_bbox_and_copy_gpkg(self):
        for gsd in self.gsd_grids_in_meter:
            output_gpkg_fp = os.path.join(
                self.processing_merge_dir, f"flow_direction_{gsd}.gpkg"
            )
            gt.crop_gpkg_by_bbox(
                output_gpkg_fp,
                f"flow_direction_{gsd}",
                self.result_dir,
                self.bbox,
                f"flow_direction_{gsd}_{self.dem_filename}.gpkg",
            )

    # ----------------------------------------------------------------------------------------------------#
    def _process_d8_flow_direction(self, args):
        fn, output_fn = args
        if not os.path.exists(output_fn):
            logger.debug(
                "[D8-Extraction] Processing: %s -> %s",
                os.path.basename(fn),
                os.path.basename(output_fn),
            )
            D8FlowDirectionExtractor.compute_d8_flow_directions(fn, output_fn)

    def _process_d8_aggregation_to_vector(self, args):
        fn, gsd, output_fn = args
        if not os.path.exists(output_fn):
            logger.debug(
                "[D8-Vectorizer] Processing: %s -> %s",
                os.path.basename(fn),
                os.path.basename(output_fn),
            )
            D8FlowDirectionExtractor.create_d8_aggregated_as_vector(
                fn, output_fn, grid_resolution=gsd, layerName=self.LAYER_NAME
            )
