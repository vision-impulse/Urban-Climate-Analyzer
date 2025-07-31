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

import osmnx as ox
import os
import pandas as pd
import logging

logger = logging.getLogger("osm_downloader")


class OSMDownloader:

    TAGS = {"landuse": ["farmland", "grass"]}

    def __init__(self, bbox, out_path):
        super(OSMDownloader, self).__init__()
        self.bbox = bbox
        self.out_path = out_path

    def run(self):
        try:
            logger.info(
                "Start resource download from OSM for tags (%s)" % (OSMDownloader.TAGS)
            )
            gdf = ox.features_from_bbox(bbox=self.bbox, tags=OSMDownloader.TAGS)
            basedir = os.path.dirname(self.out_path)
            if not os.path.exists(basedir):
                os.makedirs(basedir)
            gdf.to_file(self.out_path, driver="GeoJSON", engine="pyogrio")
        except Exception as err:
            logger.error(
                "Error occurred while downloading the file from OSM for %s %s!"
                % (OSMDownloader.TAGS, err)
            )
