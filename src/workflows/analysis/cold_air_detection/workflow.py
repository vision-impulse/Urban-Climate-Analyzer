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
import logging
import pandas as pd
import geopandas as gpd
import shutil
import hashlib

from shapely.geometry import box
from shapely.ops import unary_union
from api.osm_downloader import OSMDownloader
from api.resource_downloader import ZipDatasetDownloader
from workflows.workflow_base import BaseWorkflow

logger = logging.getLogger("cold_air_workflow")


class ColdAirZoneWorkflow(BaseWorkflow):

    RESULT_FILENAME = "cold_air_zones.gpkg"

    def __init__(
        self,
        path_config,
        city,
        bbox_4326,
        dataset_url_dgl,
        dataset_url_clc,
        override_files,
    ):
        super(ColdAirZoneWorkflow, self).__init__(
            city, path_config, bbox_4326, override_files, "cold_air_zones"
        )
        self.dataset_url_dgl = dataset_url_dgl
        self.dataset_url_clc = dataset_url_clc
        self.osm_file = os.path.join(
            self.datasets_dir,
            "osm",
            f"osm_polygons_{self._hexdigest_for_bbox(bbox_4326)}.geojson",
        )
        self.dgl_file = os.path.join(self.datasets_dir, "dgl", "V_OD_DGL.shp")
        self.clc2_file = os.path.join(
            self.datasets_dir,
            "clc",
            "clc5_2018.utm32s.shape",
            "clc5",
            "clc5_class2xx.shp",
        )
        self.clc3_file = os.path.join(
            self.datasets_dir,
            "clc",
            "clc5_2018.utm32s.shape",
            "clc5",
            "clc5_class3xx.shp",
        )
        self.bbox_gdf = self._bbox_df_from_bounds(self.bbox)

    def run(self):
        try:
            self._ensure_datasets()
            self._run_cold_air_zone_detection()
            self._copy_from_processing_to_result_dir()
        except Exception as e:
            logger.error("Error computing cold air zones: %s", e)
            pass

    # --------------------------------------------------------------------
    def _ensure_datasets(self):
        if os.path.exists(self.osm_file):
            logger.info(
                "✔ Required dataset OSM already downloaded (%s).", self.osm_file
            )
        else:
            logger.info("Required dataset OSM not found. Downloading...")
            downloader = OSMDownloader(self.bbox, self.osm_file)
            downloader.run()

        if os.path.exists(self.dgl_file):
            logger.info(
                "✔ Required dataset DGL already downloaded (%s).", self.dgl_file
            )
        else:
            logger.info("Required dataset DGL not found. Downloading...")
            downloader = ZipDatasetDownloader(
                self.dataset_url_dgl,
                self.datasets_dir,
                "dgl",
                "DGL_EPSG25832_Shape.zip",
            )
            downloader.run()

        if os.path.exists(self.clc2_file) and os.path.exists(self.clc3_file):
            logger.info(
                "✔ Required dataset CLC already downloaded (%s).", self.clc2_file
            )
        else:
            logger.info("Required dataset CLC not found. Downloading...")
            downloader = ZipDatasetDownloader(
                self.dataset_url_clc,
                self.datasets_dir,
                "clc",
                "clc5_2018.utm32s.shape.zip",
            )
            downloader.run()

    def _run_cold_air_zone_detection(self):
        output_path = os.path.join(self.processing_workflow_dir, self.RESULT_FILENAME)
        if os.path.exists(output_path) and not self.override_files:
            logger.info(
                "Cold air zones have already been computed for the requested AOI "
                "(bbox/cityname); skipping processing."
            )
            return
        self._extract_and_merge_cold_air_zones_from_lulc_maps(output_path)

    def _extract_and_merge_cold_air_zones_from_lulc_maps(self, output_path):
        # CLC Classes starting with 2 in Taxonomy
        gdf_clc_2 = gpd.read_file(self.clc2_file)
        gdf_clc_2 = gpd.clip(gdf_clc_2, self.bbox_gdf)
        gdf_clc_2 = gdf_clc_2[gdf_clc_2["CLC18"].isin(["211", "231"])]

        # CLC Classes starting with 3 in Taxonomy
        gdf_clc_3 = gpd.read_file(self.clc3_file)
        gdf_clc_3 = gpd.clip(gdf_clc_3, self.bbox_gdf)
        gdf_clc_3 = gdf_clc_3[(gdf_clc_3["CLC18"] == "321")]

        # Open Street Map
        gdf_osm = gpd.read_file(self.osm_file)
        gdf_osm = gdf_osm.to_crs(epsg=25832)
        gdf_osm = gpd.clip(gdf_osm, self.bbox_gdf)
        gdf_osm = gdf_osm[["geometry"]]

        # Dauergruenland
        gdf_dgl = gpd.read_file(self.dgl_file)
        gdf_dgl = gpd.clip(gdf_dgl, self.bbox_gdf)

        dfs = [gdf_clc_2, gdf_clc_3, gdf_osm]
        if gdf_dgl.empty:
            logger.warning(
                "AOI (bbox / cityname) lies outside of the dataset 'Dauergrünland (NRW)'; "
                "The dataset will be skipped for further processing."
            )
        else:
            dfs.append(gdf_dgl)

        crs = gdf_clc_2.crs if gdf_clc_2.crs is not None else "EPSG:25832"
        merged_df = gpd.GeoDataFrame(pd.concat(dfs, ignore_index=True), crs=crs)
        union_geom = unary_union(merged_df.geometry)
        union_gdf = gpd.GeoDataFrame(geometry=[union_geom], crs=merged_df.crs)
        union_gdf_4326 = union_gdf.to_crs(epsg=4326)
        union_gdf_4326.to_file(output_path, layer="cold_area_zones", driver="GPKG")

    def _copy_from_processing_to_result_dir(self):
        src_path = os.path.join(self.processing_workflow_dir, self.RESULT_FILENAME)
        dst_path = os.path.join(self.result_workflow_dir, self.RESULT_FILENAME)
        shutil.copyfile(src_path, dst_path)

    def _bbox_df_from_bounds(self, bbox_bounds_4326):
        bbox_geom = box(*bbox_bounds_4326)
        bbox_gdf = gpd.GeoDataFrame(geometry=[bbox_geom], crs="EPSG:4326")
        bbox_gdf = bbox_gdf.to_crs(epsg=25832)
        return bbox_gdf

    def _hexdigest_for_bbox(self, bbox):
        bbox_str = ",".join(f"{v:.10f}" for v in bbox)
        return hashlib.sha1(bbox_str.encode("utf-8")).hexdigest()
