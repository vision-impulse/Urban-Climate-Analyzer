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

import geopandas as gpd
import glob
import os

from utils.geoserver import GeoServer
from utils.postgis_importer import PostGisImporter
from config.path_config import PathConfig
from dotenv import load_dotenv

load_dotenv()


GEOSERVER_ADMIN_USER = os.getenv("GEOSERVER_ADMIN_USER")
GEOSERVER_ADMIN_PASSWORD = os.getenv("GEOSERVER_ADMIN_PASSWORD")
GEOSERVER_WORKSPACE = os.getenv("GEOSERVER_WORKSPACE")
GEOSERVER_HOST = os.getenv("GEOSERVER_HOST", "geoserver")
GEOSERVER_PORT = os.getenv("GEOSERVER_PORT", 8080)

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")


class WorkflowPublisher:

    def __init__(self, args, modules, app_config, city_config):
        self.args = args
        self.modules = modules
        self.city_name = args.city
        self.app_config = app_config
        self.city_config = city_config
        self.override_files = args.override
        self.layer_name_suffix = f"{self.city_name}_"
        self.path_config = PathConfig(app_config["output_data_dir"])
        self.result_dir = self.path_config.results
        self.server = GeoServer(
            GEOSERVER_WORKSPACE,
            "geoserver",
            GEOSERVER_PORT,
            GEOSERVER_ADMIN_USER,
            GEOSERVER_ADMIN_PASSWORD,
            POSTGRES_USER,
            POSTGRES_PASSWORD,
            POSTGRES_DB,
            POSTGRES_PORT,
        )
        self.db_importer = PostGisImporter(
            POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT
        )

    def run(self):
        self._upload_styles()
        for workflow_type in self.modules:
            if workflow_type == "land_surface_temperature":
                self.publish_lst_files()
            if workflow_type == "vegetation_indices":
                self.publish_vegetation_files()
            if workflow_type == "cold_air_zones":
                self.publish_cold_air_files()
            if workflow_type == "cold_air_zones_with_slope":
                self.publish_cold_air_files_with_slope()
            if workflow_type == "air_flow_direction":
                self.publish_air_flow_files()
            if workflow_type == "all":
                self.publish_lst_files()
                self.publish_vegetation_files()
                self.publish_cold_air_files()
                self.publish_cold_air_files_with_slope()
                self.publish_air_flow_files()

    def _upload_styles(self):
        style_folder = "./../config/geoserver_styles"
        styles = [
            os.path.join(style_folder, f)
            for f in os.listdir(style_folder)
            if f.endswith(".sld") or f.endswith(".SLD")
        ]
        self.server.create_styles(styles)

    def publish_lst_files(self):
        lst_folder = os.path.join(self.result_dir, self.city_name, "heat_islands")
        tif_files = glob.glob(os.path.join(lst_folder, "**", "*.tiff"), recursive=True)
        self.server.publish_images(tif_files, layer_name_suffix=self.layer_name_suffix)
        named_layer_pattern = rf"\b{GEOSERVER_WORKSPACE}:{self.city_name}_lst_"
        self.server.apply_style_to_named_layer(named_layer_pattern, f"{GEOSERVER_WORKSPACE}:lst")

    def publish_vegetation_files(self):
        veg_folder = os.path.join(self.result_dir, self.city_name, "vegetation_indices")
        tif_files = glob.glob(os.path.join(veg_folder, "**", "*.tiff"), recursive=True)
        self.server.publish_images(tif_files, layer_name_suffix=self.layer_name_suffix)
        named_layer_pattern = rf"\b{GEOSERVER_WORKSPACE}:{self.city_name}_ndvi_"
        self.server.apply_style_to_named_layer(named_layer_pattern, f"{GEOSERVER_WORKSPACE}:ndvi")
        named_layer_pattern = rf"\b{GEOSERVER_WORKSPACE}:{self.city_name}_ndmi_"
        self.server.apply_style_to_named_layer(named_layer_pattern, f"{GEOSERVER_WORKSPACE}:ndmi")

    def publish_cold_air_files(self):
        cold_air_zone_file = os.path.join(
            self.result_dir, self.city_name, "cold_air_zones", "cold_air_zones.gpkg"
        )
        self._publish_geopackage(cold_air_zone_file)
        named_layer_pattern = rf"\b{GEOSERVER_WORKSPACE}:{self.city_name}_cold_air_zones\b"
        self.server.apply_style_to_named_layer(named_layer_pattern, f"{GEOSERVER_WORKSPACE}:cold")

    def publish_cold_air_files_with_slope(self):
        cold_air_zone_slope_file = os.path.join(
            self.result_dir,
            self.city_name,
            "cold_air_zones_with_slope",
            "cold_air_zones_with_slope.gpkg",
        )
        self._publish_geopackage(cold_air_zone_slope_file)
        named_layer_pattern = rf"\b{GEOSERVER_WORKSPACE}:{self.city_name}_cold_air_zones_with_slope"
        self.server.apply_style_to_named_layer(named_layer_pattern, f"{GEOSERVER_WORKSPACE}:cold_slope")
        

    def publish_air_flow_files(self):
        veg_folder = os.path.join(self.result_dir, self.city_name, "flow_direction")
        gpkg_files = glob.glob(os.path.join(veg_folder, "**", "*.gpkg"), recursive=True)
        for gpkg_file in gpkg_files:
            self._publish_geopackage(gpkg_file)
        named_layer_pattern = rf"\b{GEOSERVER_WORKSPACE}:{self.city_name}_flow_direction"
        self.server.apply_style_to_named_layer(named_layer_pattern, f"{GEOSERVER_WORKSPACE}:flow_direction")

    def _publish_geopackage(self, geopackage_fp):
        tablename = (
            self.city_name + "_" + os.path.basename(geopackage_fp).replace(".gpkg", "")
        )
        geopackage_fp = geopackage_fp.replace("./../data", "/data")

        self.db_importer.import_gdf_to_postgis_table(geopackage_fp, tablename)
        self.server.publish_featurestore_layer(tablename)
