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

import numpy as np
import scipy.constants
import logging

logger = logging.getLogger("satellite_workflow")

def compute_normalized_index(band1: np.ndarray, band2: np.ndarray) -> np.ndarray:
    """
    Calculate a normalized index.
    """
    if not band1.any() or not band2.any():
        logger.error("At least one of the bands is not set")
        return np.zeros(band1.shape)

    logger.debug("Calculate normalized index.")
    index = (band1 - band2) / (band1 + band2 + 1e-10)  # Avoid division by zero
    return np.nan_to_num(index, copy=False, nan=-9999, posinf=0.0, neginf=0.0)


def compute_proportion_of_vegetation(ndvi: np.ndarray) -> np.ndarray:
    """
    Computes the potential of vegetation based on the NDVI
    """
    if not ndvi.any():
        logger.error("No NDVI was given")
        return np.zeros_like(ndvi)
    if ndvi.max() == ndvi.min():
        logger.error("NDVI is uniform. The computations will contain errors")
        return np.zeros_like(ndvi)
    potential_of_vegetation = (ndvi - ndvi.min()) / (ndvi.max() - ndvi.min())
    return potential_of_vegetation ** 2


def compute_lst(nir_band: np.ndarray, red_band: np.ndarray, tir_band: np.ndarray, tir_centerwavelength: float = 10.895) -> np.ndarray:
    """
    Calculates the land surface temperature (LST) using the Landsat Collection 2 method.
    """
    # Constants
    wave_length = tir_centerwavelength * 1e-6  # Convert micrometers to meters
    epsilon = 0.004 * compute_proportion_of_vegetation(compute_normalized_index(nir_band, red_band)) + 0.986
    epsilon = np.clip(epsilon, 0.95, 0.99)  # Ensure valid emissivity range

    # LST calculation
    lst = tir_band / (1 + (wave_length * tir_band / (scipy.constants.Planck * scipy.constants.speed_of_light / scipy.constants.Boltzmann)) * np.log(epsilon))
    lst_normalized = (lst - lst.min()) / (lst.max() - lst.min())
    return lst_normalized