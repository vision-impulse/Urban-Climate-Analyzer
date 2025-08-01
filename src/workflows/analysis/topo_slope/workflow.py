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
import geopandas as gpd
import numpy as np
import subprocess
import logging

from multiprocessing import Pool, cpu_count
from rasterio.mask import mask as rio_mask
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union
from rasterio.errors import RasterioError
from shapely.geometry import box
from workflows.workflow_base import BaseWorkflow

logger = logging.getLogger("topo_slope_workflow")


class SlopeExtractionWorkflow(BaseWorkflow):

    def __init__(
        self, path_config, city, bbox, dem_folder, override_files, dem_scale_factor=1.0
    ):

        super(SlopeExtractionWorkflow, self).__init__(city, bbox, "slope")
        self.dem_folder = dem_folder
        self.dem_scale_factor = dem_scale_factor
        self.path_config = path_config
        self.override_files = override_files
        self.processing_dir = path_config.processing
        self.city = city
        self.wflow_name = "slope"
        self.process_wflow_folder = os.path.join(
            self.processing_dir,
            self.city,
            self.wflow_name
        )
        self.slope_raster_dir = os.path.join(
            self.processing_dir,
            self.city,
            self.wflow_name,
            os.path.basename(self.dem_folder),
            "single_raster_files",
        )
        if self.override_files:
            self._remove_dir(self.process_wflow_folder)
            self._ensure_dir(self.process_wflow_folder)
        self._ensure_dir(self.slope_raster_dir)

    def run(self):
        self._extract_slope_for_dem_files()

    def _extract_slope_for_dem_files(self):
        logger.info("Processing DEM folder: %s", self.dem_folder)
        files = glob.glob(f"{self.dem_folder}/*.tif")
        tasks = [
            (
                fn,
                os.path.join(
                    self.processing_dir,
                    self.city,
                    self.wflow_name,
                    os.path.basename(self.dem_folder),
                    "single_raster_files",
                    os.path.basename(fn).replace(".tif", ".slope.tif"),
                ),
            )
            for fn in files
        ]
        logger.info("Extracting slopes with %s processes...", self.num_processes)
        with Pool(self.num_processes) as pool:
            pool.map(self._process_slope_mp, tasks)

    # --------------------------------------------------------------------------------------------------------------#
    def _process_slope_mp(self, args):
        dem_filepath, output_path = args

        if os.path.exists(output_path):
            logger.debug("%s already exists", output_path)
            return

        logger.info(
            " [Slope] Processing: %s -> %s",
            os.path.basename(dem_filepath),
            os.path.basename(output_path),
        )

        gdaldem_cmd = [
            "gdaldem",
            "slope",
            dem_filepath,
            output_path,
            "-compute_edges",
            "-s",
            str(self.dem_scale_factor),
            "-of",
            "GTiff",
        ]

        try:
            subprocess.run(gdaldem_cmd, check=True, capture_output=True, text=True)
            logger.info("GDALDEM slope computed and saved to %s", output_path)

        except FileNotFoundError:
            logger.error(
                "GDALDEM command not found. Ensure GDAL is installed and 'gdaldem' is in your PATH."
            )

        except subprocess.CalledProcessError as e:
            logger.error("Error running GDALDEM: %s", e)
            logger.debug("STDOUT: %s", e.stdout)
            logger.debug("STDERR: %s", e.stderr)

        except Exception as e:
            logger.exception("Unexpected error while processing with GDALDEM: %s", e)
