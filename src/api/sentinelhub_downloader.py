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

import logging
import os
from datetime import datetime
from typing import Optional
from requests.exceptions import HTTPError
import hashlib

from sentinelhub.api.catalog import SentinelHubCatalog
from sentinelhub.api.process import SentinelHubRequest
from sentinelhub.constants import CRS, MimeType, MosaickingOrder
from sentinelhub.data_collections import DataCollection
from sentinelhub.geo_utils import bbox_to_dimensions
from sentinelhub.geometry import BBox
from sentinelhub.config import SHConfig
from sentinelhub import BBox, CRS, UtmZoneSplitter


logger = logging.getLogger("sentinelhub_downloader")


class SentinelhubAPIClient:
    """A class which handles the connection to sentinelhub based on
    the sentinelhub python library.

    """

    def __init__(
        self,
        bbox_wgs84: tuple[float, float, float, float],
        datacollection: DataCollection,
        resolution: int,
    ):
        """Constructor for a sentinelhub_client object.

        Arguments:
            gps_cords: tuple[float,float,float,float]
                GPS-coordinates, wich describe a rectangle to build a
                bounding box with crs.
            crs: sentinelhub.constants.CRS
                The coordinate reference system
        """
        self.bbox = BBox(bbox_wgs84, CRS.WGS84)
        self.resolution = resolution
        self.collection = datacollection
        self.config = SHConfig()
        self.config.sh_base_url = self.collection.service_url
        self.catalog = SentinelHubCatalog(self.config)

    def get_available_days(
        self,
        time_interval: tuple[str, str],
        max_cloud_coverage: int = 25,
    ) -> list[str]:
        """Search for information about avaliable images in the timerange

        Before this function can be called successful,
        a catalog has to be opend.
        By default this is done in the Constructor

        Arguments:
            time_interval: tuple[str, str]
                The timeinterval, in which it is checked if there are
                images avaliable.

            max_cloud_coverage: int
                The maximum cloud coverage, which should be present
                in the images.

        """
        filter = f"eo:cloud_cover < {max_cloud_coverage}"
        search_iterator = self.catalog.search(
            collection=self.collection,
            bbox=self.bbox,
            time=time_interval,
            filter=filter,
            fields={
                "include": ["id", "properties.datetime", "properties.eo:cloud_cover"],
                "exclude": [],
            },
        )
        dates = [i["properties"]["datetime"].split("T")[0] for i in search_iterator]
        return dates

    def download_satellite_image_for_dates(
        self,
        datafolder: str | os.PathLike[str],
        requested_days: list[str],
        evalscript_path: str | os.PathLike[str],
        max_cloud_coverage: int,
    ):
        """Download satellite images for the given days

        Arguments:
            datafolder: str | os.PathLike[str]
            The folder, to which the images should be downloaded

        dates: list[str]
            A list of dates, for which data should be downloaded.
            Before the download, it is checked, if for each date an image exists.
            Currently only the format "YYYYMMDD" is supported.

        dates: list[str]
            A list of dates, for which data should be downloaded.
            Before the download, it is checked, if for each date an image exists.
            The default format is %Y%m%d
        """
        avaliable_days = self.get_available_days(
            time_interval=(min(requested_days), max(requested_days)), 
            max_cloud_coverage=max_cloud_coverage
        )
        usable_days = [day for day in avaliable_days if day in requested_days]
        logger.info("Requested dates for download: %s", requested_days)
        logger.info("Usable dates for download: %s, %s", len(usable_days), usable_days)
        self.download_by_tiling(
            datafolder, usable_days, evalscript_path, tile_size_m=5000
        )

    def download_by_tiling(
        self,
        download_folder: str | os.PathLike[str],
        potential_dates: list[str],
        evalscript_path: str | os.PathLike[str],
        tile_size_m: int = 10000,
    ):
        splitter = UtmZoneSplitter([self.bbox.geometry], self.bbox.crs, tile_size_m)
        for tile_bbox in splitter.get_bbox_list():
            for date in potential_dates:
                tile_id = self._generate_tile_id(tile_bbox, date)
                tile_output_dir = os.path.join(download_folder, date, tile_id)

                if self._is_tile_already_downloaded(tile_output_dir):
                    logger.debug("Skipping date %s, already downloaded...", date)
                    continue  # Skip if already downloaded

                os.makedirs(tile_output_dir, exist_ok=True)
                logger.debug(
                    "Download satellite image for date %s to %s...", date, tile_output_dir
                )
                self._download_satellite_image_for_date(
                    date=date,
                    data_folder=tile_output_dir,
                    evalscript_path=evalscript_path,
                    tile_bbox=tile_bbox,
                )

    def _download_satellite_image_for_date(
        self,
        date: str,
        data_folder: str | os.PathLike[str],
        evalscript_path,
        tile_bbox,
    ):
        """
        Donwloads a satellite image from sentinelhub
        The image is downloaded for the provided gps_coordinates.
        The images are directly downloaded, therefore there is no return value.

        Arguments:
            data_folder: str | os.PathLike[str]
                The folder to which the images should be downloaded.
            date:  str
                The date, for which the images should be downloaded, represented as a string.
        """
        size = bbox_to_dimensions(tile_bbox, resolution=self.resolution)

        input_data = SentinelHubRequest.input_data(
            data_collection=self.collection,
            time_interval=(date + "T00:00:00Z", date + "T23:59:59Z"),
            mosaicking_order=MosaickingOrder.LEAST_CC,
        )

        responses = SentinelHubRequest.output_response(
            identifier="default", response_format=MimeType.TIFF
        )

        evalscript = self._load_evalscript(evalscript_path)
        if evalscript == "":
            logger.error("No evalscript found to use for the download")
            return
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[input_data],
            responses=[responses],
            bbox=tile_bbox,
            size=size,
            data_folder=data_folder,
        )
        request.get_data(save_data=True)

    def _load_evalscript(self, path_to_evalscript):
        with open(path_to_evalscript, "r", encoding="utf-8") as eval_file:
            return eval_file.read()

    def _is_tile_already_downloaded(self, tile_output_dir: str) -> bool:
        if not os.path.exists(tile_output_dir):
            return False

        for subfolder in os.listdir(tile_output_dir):
            subfolder_path = os.path.join(tile_output_dir, subfolder)
            if os.path.isdir(subfolder_path):
                tiff_fp = os.path.join(subfolder_path, "request.json")
                json_fp = os.path.join(subfolder_path, "response.tiff")
                if os.path.exists(tiff_fp) and os.path.exists(json_fp):
                    return True
        return False

    def _generate_tile_id(self, bbox: BBox, date: str) -> str:
        return hashlib.md5(
            f"{bbox.min_x}_{bbox.min_y}_{bbox.max_x}_{bbox.max_y}_{date}".encode()
        ).hexdigest()


# --------------------------------------------------------------------------- #
class SentinelHubDownloader:
    def __init__(self, gps_cords, download_dir, datacollection, resolution):
        self.sh_api = SentinelhubAPIClient(
            gps_cords,
            datacollection=datacollection,
            resolution=resolution,
        )
        self.download_dir = os.path.join(download_dir, datacollection.name)

    def download_satellite_image_for_dates(
        self, 
        requested_days: list[str], 
        evalscript_path: str, 
        max_cloud_coverage: int
    ) -> None:
        self.sh_api.download_satellite_image_for_dates(
            self.download_dir, requested_days, evalscript_path, max_cloud_coverage
        )

    @classmethod
    def create_sentinel2_downloader(cls, gps_cords, download_dir):
        return cls(
            gps_cords,
            download_dir,
            datacollection=DataCollection.SENTINEL2_L2A,
            resolution=10,
        )

    @classmethod
    def create_landsat_downloader(cls, gps_cords, download_dir):
        return cls(
            gps_cords,
            download_dir,
            datacollection=DataCollection.LANDSAT_OT_L2,
            resolution=30,
        )
