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

from pathlib import Path
import os

S2_EVALSCRIPT_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../config/sentinelhub_evalscripts/sentinel.js"
    )
)
L8_EVALSCRIPT_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../config/sentinelhub_evalscripts/landsat.js"
    )
)


class PathConfig:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.processing = os.path.join(self.base_dir, "processing")
        self.results = os.path.join(self.base_dir, "results")
        self.datasets = os.path.join(self.base_dir, "datasets")
        self.downloads = os.path.join(self.base_dir, "downloads")

        # download subfolders
        self.satellite_dir = os.path.join(self.downloads, "satellite_images")
        self.landsat_dir = os.path.join(self.satellite_dir, "LANDSAT_OT_L2")
        self.sentinel_dir = os.path.join(self.satellite_dir, "SENTINEL2_L2A")
        self.weather_dir = os.path.join(self.downloads, "weather_data")

        self.ensure_directories()

    def ensure_directories(self):
        for path in [self.processing, self.results, self.datasets, self.downloads]:
            if not os.path.exists(path):
                os.makedirs(path)
