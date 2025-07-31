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
import requests 
import zipfile
import logging

logger = logging.getLogger("resource_downloader")


class ZipDatasetDownloader():

    def __init__(self, url, dataset_base_dir, dataset_name, zip_name):
        super(ZipDatasetDownloader, self).__init__()
        self.url = url
        self.dataset_base_dir = dataset_base_dir
        self.dataset_name = dataset_name
        self.zip_name = zip_name
        
    def run(self):
        dataset_dir = os.path.join(self.dataset_base_dir, self.dataset_name)        
        os.makedirs(dataset_dir)
        try:
            response = requests.get(self.url, stream=True, timeout=300)
            response.raise_for_status()

            zip_path = os.path.join(dataset_dir, self.zip_name) 
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("✔ Download complete (%s).", self.url)
        except requests.RequestException as e:
            logger.error(" Failed to download the dataset: %s", e)
            return

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(dataset_dir)
            logger.info("✔ Extraction complete to: %s", dataset_dir)
        except zipfile.BadZipFile as e:
            logger.error("Failed to extract ZIP: %s", e)
            return
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)