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

import io
import logging
import os
import zipfile
from enum import Enum
from typing import Any, Union
from urllib.parse import urljoin

import pandas as pd
import utils.date_utils as util
import io
import zipfile
import re

logger = logging.getLogger("dwd_date_extractor")


class DwDClimateExtractor:

    CLIMATE_FILENAME = r"produkt_klima_tag*"

    def __init__(self, zipfile: Union[str, os.PathLike]):
        self.zipfile = zipfile
        
    def extract_suitable_days(self, max_windspeed=2.6, min_temperature=25.0):
        if not os.path.exists(self.zipfile):
            logger.error(f"{self.zipfile} not found.")
            return []
        return self.select_days_from_climate_archive(max_windspeed=max_windspeed, min_temperature=min_temperature)

    def select_days_from_climate_archive(self, max_windspeed: float, min_temperature: float) -> list[str]:
        try:
            with zipfile.ZipFile(self.zipfile, "r") as z_file:
                # Find the file matching the pattern inside the zip
                pattern = re.compile(self.CLIMATE_FILENAME) 
                matching_files = [f for f in z_file.namelist() if pattern.match(os.path.basename(f))]

                if not matching_files:
                    raise FileNotFoundError(f"{self.CLIMATE_FILENAME} not found in ZIP archive.")

                climate_data_path = matching_files[0]
                with z_file.open(climate_data_path) as climate_file:
                    text_stream = io.TextIOWrapper(climate_file, encoding="utf-8")
                    return self._parse_climate_data(text_stream, max_windspeed, min_temperature)
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file: %s", self.zipfile)
        except Exception as e:
            logger.error("Error processing climate file: %s", e)
            raise

    def _parse_climate_data(self, file_stream, max_windspeed, min_temperature):
        """
        Filters days in a file for a maximum windspeed and a minimum
        temperature.

        Args:
            data_file (Union[str, os.PathLike]): A path to a file containing a CSV. The CSV contains
            information about the weather.
            max_windspeed (float): The maximum windspeed.
            min_temperature (float): The minimum temperature.

        Returns:
            list[str]: A list of strings representing the dates for the days,
            which match the filters.
        """
        try:
            df = pd.read_csv(file_stream, sep=";")
            
            # strip whitespace from column names and values
            df.columns = df.columns.str.strip()
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].str.strip()
            df['FM'] = pd.to_numeric(df['FM'], errors='coerce')
            df['TXK'] = pd.to_numeric(df['TXK'], errors='coerce')
            
            # Filter the DataFrame based on the conditions
            df_filtered = df[ df['FM'].notna() & df['TXK'].notna() & 
                             (df['FM'] < max_windspeed) & (df['TXK'] >= min_temperature)]
            
            date_objs = util.parse_date_strings_to_objects(df_filtered['MESS_DATUM'].astype(str).tolist())
            date_objs = util.filter_dates_after_year(date_objs, year=2023)
            date_objs = util.convert_date_objects_to_strings_yyyymmdd(date_objs)
            return date_objs
        except Exception as e:
            logger.error("Error filtering days from file: %s", e)
            return []
    
