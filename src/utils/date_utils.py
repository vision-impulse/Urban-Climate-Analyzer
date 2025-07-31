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

from datetime import datetime
import logging

logger = logging.getLogger("utils")

def convert_dates(date_strings_yyyymmdd):
    converted_dates = []
    for date_str in date_strings_yyyymmdd:
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            converted_dates.append(date_obj.strftime('%Y-%m-%d'))
        except ValueError as e:
            logger.error(f"Error processing date '{date_str}': {e}. Skipping this date.")
    return converted_dates


def parse_date_strings_to_objects(date_strings_yyyymmdd):
    """
    Parses a list of date strings (YYYYMMDD) into datetime objects.
    Handles errors for invalid date strings.

    Args:
        date_strings_yyyymmdd (list): A list of date strings in 'YYYYMMDD' format.

    Returns:
        list: A list of datetime objects.
    """
    parsed_dates = []
    for date_str in date_strings_yyyymmdd:
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            parsed_dates.append(date_obj)
        except ValueError as e:
            logger.error(f"Error processing date '{date_str}': {e}. Skipping this date.")
    return parsed_dates

def filter_dates_after_year(date_objects, year=2023, month=1, day=1):
    """
    Filters a list of datetime objects, keeping only those after a year e.g. January 1, 2023.

    Args:
        date_objects (list): A list of datetime objects.

    Returns:
        list: A list of datetime objects after 2023-01-01.
    """
    filtered_dates = []
    threshold_date = datetime(year, 1, 1)
    for date_obj in date_objects:
        if date_obj > threshold_date:
            filtered_dates.append(date_obj)
    return filtered_dates

def convert_date_objects_to_strings_yyyymmdd(date_objects):
    """
    Converts a list of datetime objects into date strings (YYYY-MM-DD).

    Args:
        date_objects (list): A list of datetime objects.

    Returns:
        list: A list of date strings in 'YYYY-MM-DD' format.
    """
    return [date_obj.strftime('%Y-%m-%d') for date_obj in date_objects]
