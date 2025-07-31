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
import logging

from api.dwd_downloader import DWDFileDownloader
from workflows.satellite_acquisition.dwd_date_extractor import DwDClimateExtractor
from glob import glob
from sentinelhub import UtmZoneSplitter, BBox
from sentinelhub.constants import CRS
from datetime import datetime
from config.path_config import S2_EVALSCRIPT_FILE, L8_EVALSCRIPT_FILE
from api.sentinelhub_downloader import SentinelHubDownloader

logger = logging.getLogger("satellite_acquisition")


class DataAcquisitionWorkflow:

    def __init__(
        self,
        path_config,
        bbox,
        dwd_base_url,
        dwd_resource_filename,
        max_windspeed=2.6,
        min_temperature=25.0,
        max_cloud_coverage=25,             
        use_historical_data=False,
    ):
        self.path_config = path_config
        self.bbox = bbox
        self.dwd_base_url = dwd_base_url
        self.dwd_resource_filename = dwd_resource_filename
        self.max_windspeed = max_windspeed
        self.min_temperature = min_temperature
        self.use_historical_data = use_historical_data

    def run(self, override=False):
        dwd_file = self._download_dwd_climate_file(override)
        dates = self._determine_dates_from_dwd_file(dwd_file)
        self._download_satellite_images_for_dates(dates)

    def _download_satellite_images_for_dates():
        raise NotImplementedError()

    def _download_dwd_climate_file(self, override):
        current_date = datetime.now().strftime("%Y_%m_%d")
        if self.use_historical_data:
            current_date = datetime.now().strftime("historical_%Y_%m_%d")
        dwd_output_fp = os.path.join(
            self.path_config.weather_dir, f"dwd_klima_{current_date}.zip"
        )

        if os.path.exists(dwd_output_fp) and not override:
            logger.info("DWD File %s already exists, skipping Download!", dwd_output_fp)
            return dwd_output_fp

        logger.info("Downloading new DWD File %s!", dwd_output_fp)
        downloader = DWDFileDownloader(self.dwd_base_url, self.dwd_resource_filename)
        downloader.download_climate_observations(dwd_output_fp)
        return dwd_output_fp

    def _determine_dates_from_dwd_file(self, dwd_fp):
        extractor = DwDClimateExtractor(dwd_fp)
        potential_dates = extractor.extract_suitable_days(
            max_windspeed=self.max_windspeed, min_temperature=self.min_temperature
        )
        return potential_dates


class LandsatSatelliteAcquisitionWorkflow(DataAcquisitionWorkflow):

    def __init__(
        self,
        path_config,
        bbox,
        dwd_base_url,
        dwd_resource_filename,
        max_windspeed,
        min_temperature,
        max_cloud_coverage,
        use_historical_data,
    ):
        super(LandsatSatelliteAcquisitionWorkflow, self).__init__(
            path_config,
            bbox,
            dwd_base_url,
            dwd_resource_filename,
            max_windspeed,
            min_temperature,
            max_cloud_coverage,
            use_historical_data,
        )

    def _download_satellite_images_for_dates(self, dates):
        downloader = SentinelHubDownloader.create_landsat_downloader(
            self.bbox, self.path_config.satellite_dir
        )
        downloader.download_satellite_image_for_dates(
            dates, evalscript_path=L8_EVALSCRIPT_FILE
        )


class SentinelSatelliteAcquisitionWorkflow(DataAcquisitionWorkflow):

    def __init__(
        self,
        path_config,
        bbox,
        dwd_base_url,
        dwd_resource_filename,
        max_windspeed,
        min_temperature,
        max_cloud_coverage,
        use_historical_data,
    ):
        super(SentinelSatelliteAcquisitionWorkflow, self).__init__(
            path_config,
            bbox,
            dwd_base_url,
            dwd_resource_filename,
            max_windspeed,
            min_temperature,
            max_cloud_coverage,
            use_historical_data,
        )

    def _download_satellite_images_for_dates(self, dates):
        downloader = SentinelHubDownloader.create_sentinel2_downloader(
            self.bbox, self.path_config.satellite_dir
        )
        downloader.download_satellite_image_for_dates(
            dates, evalscript_path=S2_EVALSCRIPT_FILE
        )
