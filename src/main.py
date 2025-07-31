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

import argparse
import os
import logging
import sys

from dotenv import load_dotenv
from config.app_config import load_app_config, load_city_config
from config.logging_config import setup_logging

from workflows.workflow_runner import WorkflowRunner
from workflows.workflow_publisher import WorkflowPublisher

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Load .env file for API keys and external services
load_dotenv()

# Mapping of moduels and german alternatives
MODULE_ALIASES = {
    "lst": "land_surface_temperature",
    "veg": "vegetation_indices",
    "cold": "cold_air_zones",
    "cold_slope": "cold_air_zones_with_slope",
    "flow": "air_flow_direction",
    "hitzeinseln": "land_surface_temperature",
    "vegetation": "vegetation_indices",
    "kaltluft": "cold_air_zones",
    "kaltluft_hangneigung": "cold_air_zones_with_slope",
    "flussrichtung": "air_flow_direction",
    "alle": "all",
}

VALID_MODULES = {
    "land_surface_temperature",
    "vegetation_indices",
    "cold_air_zones",
    "cold_air_zones_with_slope",
    "air_flow_direction",
    "all",
}


def resolve_modules(user_input: str):
    raw_modules = [m.strip() for m in user_input.split(",")]
    resolved = []
    available_modules = ', '.join(sorted(VALID_MODULES | set(MODULE_ALIASES.keys())))

    for mod in raw_modules:
        mod_resolved = MODULE_ALIASES.get(mod, mod)
        if mod_resolved not in VALID_MODULES:
            logger.error("Ungültiges Modul angegeben: %s", mod)
            logger.error("Verfügbare Module: %s", available_modules)
            sys.exit(1)
        resolved.append(mod_resolved)
    # avoid duplicates!
    return list(set(resolved))


def main():
    parser = argparse.ArgumentParser(
        description="Python CLI für stadtklimatische Analysen"
    )

    parser.add_argument(
        "--city",
        required=True,
        help="Name der Stadt / Untersuchungsregion (entspricht einer Datei config/<city>.yaml)",
    )

    parser.add_argument(
        "--modules",
        required=True,
        help="Kommagetrennte Liste von Modulen (z.B. lst,cold,flow oder 'all'). Kürzel und deutsche Namen sind erlaubt.",
    )

    parser.add_argument(
        "--use_historical_data",
        action="store_true",
        help="Verwende historische Wetterdaten (Standard: nur aktuelle Daten)",
    )

    parser.add_argument(
        "--upload_to_geoserver",
        action="store_true",
        help="Ergebnisse automatisch zum GeoServer hochladen (Standard: False)",
    )

    parser.add_argument(
        "--override",
        action="store_true",
        help="Vorhandene Ergebnisse werden überschreiben (Standard: False)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Aktiviere detaillierte Ausgaben im Terminal (Debug/Info)",
    )

    args = parser.parse_args()

    selected_modules = resolve_modules(args.modules)

    # Load configs
    city_config_fp = "./../config/%s.yaml" % (args.city)
    if not os.path.exists(city_config_fp):
        logger.info("Stadtconfig wurde nicht gefunden: %s", city_config_fp)
        exit(0)

    app_config = load_app_config("./../config/app.yaml")
    city_config = load_city_config(city_config_fp)

    # Ausgabe zur Kontrolle (kann durch Logging ersetzt werden)
    logger.info("=" * 60)
    logger.info("Starte verarbeitung für: %s", args.city)
    logger.info("Ausgewählte Module: %s", selected_modules)
    logger.info("Historische Daten: %s", args.use_historical_data)
    logger.info("GeoServer Upload: %s", args.upload_to_geoserver)
    logger.info("Überschreiben erlaubt: %s", args.override)
    logger.info("City config: %s", city_config)

    # Run the workflow modules and publish results
    workflow_runner = WorkflowRunner(args, selected_modules, app_config, city_config)
    workflow_runner.run()

    if args.upload_to_geoserver:
        workflow_publisher = WorkflowPublisher(
            args, selected_modules, app_config, city_config
        )
        workflow_publisher.run()


if __name__ == "__main__":
    main()
