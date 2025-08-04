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
import os
import logging
import requests
import re

from geo.Geoserver import Geoserver
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("geoserver")


class GeoServer(object):

    def __init__(
        self,
        geoserver_workspace_name,
        geoserver_host,
        geoserver_port,
        geoserver_admin,
        geoserver_password,
        postgis_user,
        postgis_password,
        postgis_db,
        postgis_port,
    ):
        self.workspace_name = geoserver_workspace_name
        self.geoserver_admin = geoserver_admin
        self.geoserver_password = geoserver_password
        self.postgis_user = postgis_user
        self.postgis_password = postgis_password
        self.postgis_db = postgis_db
        self.postgis_port = postgis_port
        self.postgis_host = "postgis" # Docker hostname!
        self.srv = Geoserver(
            "http://%s:%s/geoserver" % (geoserver_host, geoserver_port),
            username=geoserver_admin,
            password=geoserver_password,
        )
        self.geoserver_rest_url = "http://%s:%s/geoserver/rest" % (
            geoserver_host,
            geoserver_port,
        )
        self.datastore_name = "POSTGIS_STORE"
        self._setup_workspace()
        self._create_datastore(self.datastore_name)

    def create_styles(self, style_files):
        for fp in style_files:
            self._create_style(fp)

    def publish_images(self, image_files, layer_name_suffix=None):
        for fp in image_files:
            fn = os.path.basename(fp)
            layer_name = fn.replace(".tiff", "").replace(".TIF", "").replace(".tif", "")
            if layer_name_suffix is not None:
                layer_name = layer_name_suffix + layer_name
            self.srv.create_coveragestore(
                layer_name=layer_name, path=fp, workspace=self.workspace_name
            )

    def publish_featurestore_layer(self, table_name):
        layers = self.srv.get_layers()
        layer_exists = False
        if layers["layers"] != "":
            for wl in layers["layers"]["layer"]:
                if wl["name"] == "%s:%s" % (self.workspace_name, table_name):
                    layer_exists = True
                    break
        if layer_exists:
            self.srv.delete_layer(layer_name=table_name, workspace=self.workspace_name)
        self.srv.publish_featurestore(
            workspace=self.workspace_name,
            store_name=self.datastore_name,
            pg_table=table_name,
        )
        logger.info("Published featurestore from table: %s", table_name)

    # --------------------------------------------------------------------------------------------------- #
    def _setup_workspace(self):
        workspace_exists = False
        workspaces = self.srv.get_workspaces()

        if workspaces["workspaces"] == "":
            logger.info(f"Creating new workspace {self.workspace_name}")
            _workspace = self.srv.create_workspace(workspace=self.workspace_name)
        else:
            if isinstance(workspaces, dict):
                try:
                    for w in workspaces["workspaces"]["workspace"]:
                        if w["name"] == self.workspace_name:
                            workspace_exists = True
                            break
                except Exception as e:
                    logger.error(
                        f"ERROR: Unexpected structure in get_workspaces() response: {e}"
                    )
                    return
            else:
                logger.error("ERROR: get_workspaces() did not return a dictionary.")

            if not workspace_exists:
                logger.info(f"Creating new workspace {self.workspace_name}")
                self.srv.create_workspace(workspace=self.workspace_name)

    def _create_layers(self, datastore_name, table_name):
        layers = self.srv.get_layers()
        layer_exists = False
        if layers["layers"] != "":
            for w in layers["layers"]["layer"]:
                if w["name"] == "%s:%s" % (self.workspace_name, table_name):
                    layer_exists = True
                    break
        if layer_exists:
            self.srv.delete_layer(layer_name=table_name, workspace=self.workspace_name)
        self.srv.publish_featurestore(
            workspace=self.workspace_name,
            store_name=datastore_name,
            pg_table=table_name,
        )
        logger.info(f"Creating new Featurestore {table_name}")

    def _create_style(self, style_fp):
        logger.info(f"Importing style {style_fp}")
        style_name = os.path.basename(style_fp.replace(".sld", "").replace("SLD", ""))
        styles = self.srv.get_styles(workspace=self.workspace_name)
        style_exists = False

        if styles["styles"] != "":
            for w in styles["styles"]["style"]:
                if w["name"] == style_name:
                    style_exists = True
                    break
        if style_exists:
            logger.info(f"Delete style {style_name}")
            self.srv.delete_style(style_name=style_name, workspace=self.workspace_name)

        logger.info(f"Upload style {style_name}")
        self.srv.upload_style(path=style_fp, workspace=self.workspace_name)

    def apply_style_to_named_layer(self, named_layer_pattern, style_name):
        layers = self.srv.get_layers()
        if layers["layers"] != "":
            for w in layers["layers"]["layer"]:
                if re.search(named_layer_pattern, w["name"]):
                    name = w["name"].replace(self.workspace_name + ":", "")
                    logger.info(f"Publish layer {name} with style {style_name}")
                    self.srv.publish_style(
                        layer_name=name,
                        style_name=style_name,
                        workspace=self.workspace_name,
                    )

    def _create_datastore(self, datastore_name):
        datastores = self.srv.get_datastores()
        datastore_exists = False
        if datastores["dataStores"] != "":
            for w in datastores["dataStores"]["dataStore"]:
                if w["name"] == datastore_name:
                    datastore_exists = True
                    break
        if datastore_exists:
            return 
        datastore_xml = f"""
            <dataStore>
            <name>{datastore_name}</name>
            <connectionParameters>
                <host>{self.postgis_host}</host>
                <port>{self.postgis_port}</port>
                <database>{self.postgis_db}</database>
                <user>{self.postgis_user}</user>
                <passwd>{self.postgis_password}</passwd>
                <dbtype>postgis</dbtype>
                <schema>public</schema>
            </connectionParameters>
            </dataStore>
            """
        r = requests.post(
            f"{self.geoserver_rest_url}/workspaces/{self.workspace_name}/datastores",
            headers={"Content-Type": "text/xml"},
            data=datastore_xml,
            auth=HTTPBasicAuth(self.geoserver_admin, self.geoserver_password),
        )
        logger.info(f"Created datastore: %s  (%s)", datastore_name, r.status_code)
