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

import psycopg2
import logging
import subprocess

from sqlalchemy import create_engine, text

logger = logging.getLogger("postgis_importer")


class PostGisImporter(object):

    def __init__(self, user, password, db_name, port):
        self.host = "postgis"
        self.port = port
        self.user = user
        self.db_name = db_name
        self.password = password
        self.db_url = f"postgresql://{user}:{password}@{self.host}:{port}/{db_name}"
        self.engine = create_engine(self.db_url)
        with self.engine.begin() as conn:  
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    def import_gdf_to_postgis_table(self, geopackage_fp, tablename):
        self.ogr2ogr_to_postgis(geopackage_fp, tablename)
        logger.info(
            "Geopackage successfully imported to the database (Table: %s)", tablename
        )
        try:
            with self.engine.begin() as connection:
                result = connection.execute(
                    text(
                        f"""
                    CREATE INDEX IF NOT EXISTS idx_{tablename}_geometry
                    ON {tablename} USING GIST (geometry);
                """
                    )
                )
                logger.info("Index created on %s for geometry.", tablename)
        except Exception as e:
            logger.error("Error during index creation: %s", e)


    def ogr2ogr_to_postgis(
        self,
        src_path: str,
        table_name: str,
        srid: int = 4326,
        geometry_name: str = "geometry",
        fid_name: str = "gid",
    ) -> None:
        pg_conn = (
            f'PG:host={self.host} port={self.port} dbname={self.db_name} user={self.user} password={self.password}'
        )
        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            pg_conn,
            src_path,
            "-nln", table_name,
            "-overwrite"
        ]
        
        cmd += [
            "-lco", f"GEOMETRY_NAME={geometry_name}",
            "-lco", f"FID={fid_name}",
            "-lco", "PRECISION=NO",
            "-t_srs", f"EPSG:{srid}",
            "-progress",
        ]
        
        try:
            result = subprocess.run(cmd, check=True, text=True, capture_output=True)
            logger.info("Importing data to database (%s)", result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to import data to database (%s)", e.returncode)
            logger.error("Error (%s)", result.stderr)
        