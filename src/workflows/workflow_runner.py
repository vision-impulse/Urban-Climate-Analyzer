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

import logging

from workflows.analysis.satellite_analysis.satellite_processing_workflow import (
    LandSurfaceTemperaturProcessingWorkflow,
    VegetationIndicesProcessingWorkflow,
)
from workflows.satellite_acquisition.satellite_acquisition_workflow import (
    LandsatSatelliteAcquisitionWorkflow,
    SentinelSatelliteAcquisitionWorkflow,
)
from workflows.analysis.cold_air_detection.workflow import (
    ColdAirZoneWorkflow,
)
from workflows.analysis.cold_air_with_slope_detection.workflow import (
    ColdAirZoneWithSlopeWorkflow,
)
from workflows.analysis.topo_flow_direction.flow_direction_extraction_workflow import (
    FlowDirectionWorkflow,
)
from utils.geo_tools import get_aoi_bbox_by_city_name
from config.path_config import PathConfig

logger = logging.getLogger("workflow_runner")


class WorkflowRunner:

    def __init__(self, args, modules, app_config, city_config):
        self.args = args
        self.modules = modules
        self.app_config = app_config
        self.city_config = city_config
        self.use_historical_data = args.use_historical_data
        self.override_files = args.override
        self.bbox = self._get_bbox_for_area_of_interest()
        self.city_name = args.city
        self.path_config = PathConfig(app_config["output_data_dir"])

    def run(self):
        for workflow_type in self.modules:
            if workflow_type == "land_surface_temperature":
                self.run_workflow_land_surface_temperature()
            if workflow_type == "vegetation_indices":
                self.run_workflow_vegetation_indices()
            if workflow_type == "cold_air_zones":
                self.run_workflow_cold_air_zones()
            if workflow_type == "air_flow_direction":
                self.run_workflow_air_flow_direction()
            if workflow_type == "cold_air_zones_with_slope":
                self.run_workflow_cold_air_zones_with_slope()
            if workflow_type == "all":
                self.run_workflow_land_surface_temperature()
                self.run_workflow_vegetation_indices()
                self.run_workflow_cold_air_zones()
                self.run_workflow_air_flow_direction()
                self.run_workflow_cold_air_zones_with_slope()

    def run_workflow_land_surface_temperature(self):
        logger.info(f"Executing workflow 'land_surface_temperature'")
        args = self._get_satellite_aquisition_args()
        acquisition_workflow = LandsatSatelliteAcquisitionWorkflow(**args)
        acquisition_workflow.run()
        args = self._get_satellite_processing_args()
        processing_workflow = LandSurfaceTemperaturProcessingWorkflow(**args)
        processing_workflow.run()

    def run_workflow_vegetation_indices(self):
        logger.info(f"Executing workflow 'vegetation_indices'")
        args = self._get_satellite_aquisition_args()
        acquisition_workflow = SentinelSatelliteAcquisitionWorkflow(**args)
        acquisition_workflow.run()
        args = self._get_satellite_processing_args()
        processing_workflow = VegetationIndicesProcessingWorkflow(**args)
        processing_workflow.run()

    def run_workflow_cold_air_zones(self):
        logger.info(f"Executing workflow 'cold_air_zones'")
        args = self._get_cold_air_args()
        processing_workflow = ColdAirZoneWorkflow(**args)
        processing_workflow.run()

    def run_workflow_air_flow_direction(self):
        logger.info(f"Executing workflow 'air_flow_direction'")
        self._check_dem_folder_consistency()
        for dem_folder in self.city_config["data_sources"]["local_dem_data_dirs"]:
            args = self._get_flow_direction_args(dem_folder)
            processing_workflow = FlowDirectionWorkflow(**args)
            processing_workflow.run()

    def run_workflow_cold_air_zones_with_slope(self):
        logger.info(f"Executing workflow 'cold_air_zones_with_slope'")
        self._check_dem_folder_consistency()
        for dem_folder in self.city_config["data_sources"]["local_dem_data_dirs"]:
            args = self._get_cold_air_with_slope_args(dem_folder)
            processing_workflow = ColdAirZoneWithSlopeWorkflow(**args)
            processing_workflow.run()

    ## ---------------------------------------------------------------------- #
    def _check_dem_folder_consistency(self):
        msg = "Bitte einen Ordner mit Höhenbildern in der Konfigurationsdatei angeben " \
        "unter 'data_sources -> local_dem_data_dirs -> Pfad zum Ordner'"
        if "local_dem_data_dirs" not in self.city_config["data_sources"]:
            logging.error(msg)
            exit(1)
        if (
            "local_dem_data_dirs" in self.city_config["data_sources"]
            and self.city_config["data_sources"]["local_dem_data_dirs"] is None
        ):
            logging.error(msg)
            exit(1)

    def _get_bbox_for_area_of_interest(self):
        if "bbox" in self.city_config["aoi"]:
            return self.city_config["aoi"]["bbox"]

        city_name = self.city_config["aoi"].get("city_name")
        buffer_m = self.city_config["aoi"].get("polygon_buffer_in_meter", 5000)
        return get_aoi_bbox_by_city_name(city_name, buffer_m)

    def _get_satellite_aquisition_args(self):
        dwd_url = self.app_config["data_sources"]["dwd_url_recent_data"]
        dwd_filename = self.city_config["data_sources"][
            "dwd_weatherstation_filename_recent"
        ]
        if self.use_historical_data:
            dwd_url = self.app_config["data_sources"]["dwd_url_historical_data"]
            dwd_filename = self.city_config["data_sources"][
                "dwd_weatherstation_filename_historical"
            ]
        return {
            "path_config": self.path_config,
            "bbox": self.bbox,
            "dwd_base_url": dwd_url,
            "dwd_resource_filename": dwd_filename,
            "max_windspeed": self.app_config["thresholds"]["date_filter"][
                "max_windspeed"
            ],
            "min_temperature": self.app_config["thresholds"]["date_filter"][
                "min_temperature"
            ],
            "max_cloud_coverage": self.app_config["thresholds"]["satellite_filter"][
                "max_cloud_coverage"
            ],
            "use_historical_data": self.use_historical_data,
        }

    def _get_satellite_processing_args(self):
        return {
            "path_config": self.path_config,
            "city": self.city_name,
            "bbox": self.bbox,
            "override_files": self.override_files,
        }

    def _get_cold_air_args(self):
        return {
            "path_config": self.path_config,
            "city": self.city_name,
            "bbox_4326": self.bbox,
            "dataset_url_clc": self.app_config["data_sources"]["dataset_url_clc"],
            "dataset_url_dgl": self.app_config["data_sources"]["dataset_url_dgl"],
            "override_files": self.override_files,
            
        }

    def _get_cold_air_with_slope_args(self, dem_folder):
        return {
            "path_config": self.path_config,
            "city": self.city_name,
            "bbox": self.bbox,
            "dataset_url_clc": self.app_config["data_sources"]["dataset_url_clc"],
            "dataset_url_dgl": self.app_config["data_sources"]["dataset_url_dgl"],
            "dem_folder": dem_folder,
            "override_files": self.override_files,
            "dem_scale_factor": 1.0,
        }

    def _get_flow_direction_args(self, dem_folder):
        return {
            "path_config": self.path_config,
            "city": self.city_name,
            "bbox": self.bbox,
            "dem_folder": dem_folder,
            "dem_scale_factor": 1.0,
            "override_files": self.override_files,
        }
