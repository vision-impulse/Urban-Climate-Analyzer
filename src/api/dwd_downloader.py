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

import configparser
import glob
import io
import logging
import os
import zipfile
from enum import Enum
from typing import Any, Union
from urllib.parse import urljoin

import pandas as pd
import requests

logger = logging.getLogger("dwd_downloader")


class DWDFileDownloader:

    def __init__(self, d_domain, d_filename):
        self.url = urljoin(f"{d_domain}", d_filename)

    def download_climate_observations(self, output_file_path) -> Union[bytes, None]:
        try:
            response = requests.get(url=self.url, timeout=500)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            if response.status_code == 200:
                logger.info("Successfully downloaded weather data")

                # Ensure the output folder exists
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                logger.info(
                    "Ensured output folder exists: %s",
                    os.path.dirname(output_file_path),
                )

                # Write the content to the file in binary mode ('wb')
                with open(output_file_path, "wb") as f:
                    f.write(response.content)
                logger.info("Successfully saved weather data to: %s", output_file_path)
                return output_file_path
            else:
                logger.warning(
                    "Failed to download data. Status code: %s", response.status_code
                )
                return None
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error occurred: %s", e)
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error occurred: %s", e)
            return None
        except requests.exceptions.Timeout as e:
            logger.error("Request timed out: %s", e)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("An unexpected request error occurred: %s", e)
            return None
        except IOError as e:
            logger.error("Error saving file to disk: %s", e)
            return None
        except Exception as e:
            logger.error("An unknown error occurred: %s", e)
            return None
