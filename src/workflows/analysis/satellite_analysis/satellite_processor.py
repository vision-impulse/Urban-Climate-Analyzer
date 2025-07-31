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

import json
import os
import re
import ast
import rasterio
import numpy as np
import logging
from .satellite_indices import compute_normalized_index, compute_lst
from abc import ABC, abstractmethod

logger = logging.getLogger("satellite_workflow")

tir_center_wavelength = 10.895


class SensorProcessingStrategy(ABC):
    """
    Abstract base class for sensor-specific processing logic.
    Available band information is extracted from the requested SentinelHub-Evalscript.js.
    """

    def __init__(self, eval_script):
        self.eval_script = eval_script
        self.band_order = self._extract_band_order()

    @abstractmethod
    def map_band_names(
        self, bands_data: dict[str, np.ndarray]
    ) -> dict[str, np.ndarray]:
        """
        Map actual band names to generic names (e.g., red, nir, tir).
        """
        pass

    @abstractmethod
    def compute_indices(
        self, mapped_bands: dict[str, np.ndarray]
    ) -> dict[str, np.ndarray]:
        """
        Compute specific indices (NDVI, LST) based on the mapped bands.
        """
        pass

    def _extract_band_order(self) -> list[str]:
        with open(self.eval_script, "r", encoding="utf-8") as f:
            js_code = f.read()

        # Match the bands array inside the input setup
        match = re.search(r"bands\s*:\s*(\[[^\]]*\])", js_code)
        if not match:
            raise ValueError("No 'bands' array found in JavaScript code.")

        # Convert JavaScript-style array to Python list using ast.literal_eval
        band_array_str = match.group(1)
        # Replace JS-style double quotes with Python-style single quotes
        band_array_str = band_array_str.replace('"', "'")

        try:
            band_list = ast.literal_eval(band_array_str)
        except Exception as e:
            raise ValueError("Failed to parse band list.") from e
        return band_list


class SentinelProcessor(SensorProcessingStrategy):
    NDVI = "ndvi"
    NDMI = "ndmi"

    def __init__(self, eval_script):
        super(SentinelProcessor, self).__init__(eval_script)

    def map_band_names(self, bands_data):
        return {
            "red": bands_data["B04"],
            "nir": bands_data["B08"],
            "swir": bands_data["B11"],
        }

    def compute_indices(self, mapped_bands, requested_indices):
        results = {}
        if self.NDVI in requested_indices:
            results[self.NDVI] = compute_normalized_index(
                mapped_bands["nir"], mapped_bands["red"]
            )
        if self.NDMI in requested_indices:
            results[self.NDMI] = compute_normalized_index(
                mapped_bands["nir"], mapped_bands["swir"]
            )
        return results


class LandsatProcessor(SensorProcessingStrategy):
    NDVI = "ndvi"
    LST = "lst"

    def __init__(self, eval_script):
        super(LandsatProcessor, self).__init__(eval_script)

    def map_band_names(self, bands_data):
        return {
            "red": bands_data["B04"],
            "nir": bands_data["B05"],
            "sir": bands_data["B07"],
            "tir": bands_data["B10"],
        }

    def compute_indices(self, mapped_bands, requested_indices):
        results = {}
        if self.NDVI in requested_indices:
            results[self.NDVI] = compute_normalized_index(
                mapped_bands["nir"], mapped_bands["red"]
            )
        if self.LST in requested_indices:
            ndvi = compute_normalized_index(mapped_bands["nir"], mapped_bands["red"])
            results[self.LST] = compute_lst(
                ndvi, mapped_bands["tir"], tir_center_wavelength
            )
        return results


class SatelliteImageProcessor:
    def __init__(self, tiff_path: str):
        self.tiff_path = tiff_path
        self.ref_profile = None

    def process(self, strategy: SensorProcessingStrategy, requested_indices: list[str]):
        bands_data, self.ref_profile = self._load_bands(strategy.band_order)
        mapped_bands = strategy.map_band_names(bands_data)
        self.results = strategy.compute_indices(mapped_bands, requested_indices)

    def save_index_result_to_file(self, index, output_path):
        if os.path.exists(output_path):
            return
        output_profile = self._output_profile(self.ref_profile)
        for index_name, index_data in self.results.items():
            if index == index_name:
                self._save_geotiff(output_path, index_data, output_profile)

    def _load_bands(self, band_order: list[str]) -> dict[str, np.ndarray]:
        with rasterio.open(self.tiff_path) as src:
            bands_data = {}
            for idx, band_name in enumerate(band_order):
                bands_data[band_name] = src.read(idx + 1)
            return bands_data, src.profile

    def _save_geotiff(self, output_path: str, data: np.ndarray, profile: dict):
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data.astype(np.float32), 1)
        logger.info("Saved processed satellite image to %s.", output_path)

    def _output_profile(self, reference_profile):
        profile = reference_profile.copy()
        profile.update(
            {"count": 1, "dtype": "float32", "compress": "deflate", "no-data": -9999}
        )
        return profile
