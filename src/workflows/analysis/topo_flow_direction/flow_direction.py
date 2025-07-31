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
import rasterio
import geopandas as gpd

from rasterio.windows import Window
from rasterio import Affine
from shapely.geometry import Point
from collections import Counter


D8_VALUES = [1, 2, 4, 8, 16, 32, 64, 128]


class D8FlowDirectionExtractor:

    @staticmethod
    def compute_d8_flow_directions(input_path, output_path):
        """
        Computes D8 flow directions from a DEM directly using rasterio and numpy.
        Directions are encoded as:
        North: 64, Northeast: 128, East: 1, Southeast: 2,
        South: 4, Southwest: 8, West: 16, Northwest: 32

        # N (64): (-1, 0)
        # NE (128): (-1, 1)
        # E (1): (0, 1)
        # SE (2): (1, 1)
        # S (4): (1, 0)
        # SW (8): (1, -1)
        # W (16): (0, -1)
        # NW (32): (-1, -1)

        Args:
            input_path (str): Path to the input DEM GeoTIFF file.
            output_path (str): Path to save the output D8 flow direction GeoTIFF file.
        """

        with rasterio.open(input_path) as src:
            dem = src.read(1)
            profile = src.profile
            nodata_val = profile.get("nodata")

        # Handle nodata values: replace them with NaN for calculations
        if nodata_val is not None:
            dem = dem.astype(np.float32)  # Ensure float type to use NaN
            dem[dem == nodata_val] = np.nan

        rows, cols = dem.shape
        fdir = np.zeros(
            (rows, cols), dtype=np.uint8
        )  # D8 directions are non-negative integers

        # Define direction weights and offsets based on the provided encoding
        direction_codes = {
            (0, 1): 1,  # East
            (1, 1): 2,  # Southeast
            (1, 0): 4,  # South
            (1, -1): 8,  # Southwest
            (0, -1): 16,  # West
            (-1, -1): 32,  # Northwest
            (-1, 0): 64,  # North
            (-1, 1): 128,  # Northeast
        }

        # Iterate over each cell, excluding borders
        # Border cells will remain 0 (nodata for flow direction)
        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                if np.isnan(dem[r, c]):
                    fdir[r, c] = 0  # No data
                    continue

                central_val = dem[r, c]
                max_drop = -np.inf  # Initialize with negative infinity
                steepest_direction_code = 0

                # Iterate over 3x3 neighborhood (excluding center)
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue  # Skip central cell

                        neighbor_val = dem[r + dr, c + dc]

                        if np.isnan(neighbor_val):
                            continue  # Skip nodata neighbors

                        # Calculate drop. Adjust for diagonal distance if needed, but D8 usually
                        # just uses raw elevation difference for steepest descent without distance.
                        # Here we just use elevation difference.
                        drop = central_val - neighbor_val

                        if drop > max_drop:
                            max_drop = drop
                            steepest_direction_code = direction_codes.get(
                                (dr, dc), 0
                            )  # Get code, default to 0 if not found

                # If no drop was found (e.g., surrounded by higher or equal elevation, or nodata)
                # and the cell itself is not nodata, it's a sink, so flow direction remains 0
                if max_drop <= 0:  # If there's no positive drop, it's a flat or sink
                    fdir[r, c] = 0  # This cell is a local minimum or flat
                else:
                    fdir[r, c] = steepest_direction_code

        profile.update(
            dtype=fdir.dtype,
            count=1,
            nodata=0,  # Use 0 as nodata for flow direction, as per standard practice
        )

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(fdir, 1)

    @staticmethod
    def get_mode_direction(values):
        """Return the most common D8 direction in the array."""
        values = values.flatten()
        values = values[np.isin(values, D8_VALUES)]  # Filter valid directions
        if len(values) == 0:
            return None
        count = Counter(values)
        return count.most_common(1)[0][0]

    @staticmethod
    def create_d8_aggregated_as_vector(
        input_tif, output_vector, grid_resolution=20, layerName="direction"
    ):
        with rasterio.open(input_tif) as src:
            data = src.read(1)
            transform = src.transform
            crs = src.crs
            width = src.width
            height = src.height

            pixel_size = transform.a  # assumes square pixels
            block_size = int(grid_resolution / pixel_size)

            points = []
            values = []

            for row in range(0, height, block_size):
                for col in range(0, width, block_size):
                    window = data[row : row + block_size, col : col + block_size]
                    mode_dir = D8FlowDirectionExtractor.get_mode_direction(window)
                    if mode_dir is None:
                        continue

                    # Get center coordinates of the block
                    x, y = transform * (col + block_size / 2, row + block_size / 2)
                    points.append(Point(x, y))
                    values.append(mode_dir)

        gdf = gpd.GeoDataFrame({layerName: values}, geometry=points, crs=crs)
        gdf.to_file(
            output_vector,
            driver="GPKG" if output_vector.endswith(".gpkg") else "ESRI Shapefile",
        )
