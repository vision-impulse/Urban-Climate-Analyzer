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
import shutil
import logging

from pathlib import Path
from abc import ABC, abstractmethod
from multiprocessing import cpu_count

logger = logging.getLogger("workflow_base")


class BaseWorkflow(ABC):
    def __init__(
        self, city, path_config, bbox_4326, override_files, workflow_name: str
    ):
        self.city = city
        self.path_config = path_config
        self.bbox = bbox_4326
        self.override_files = override_files
        self.wflow_name = workflow_name
        self.num_processes = cpu_count()
        self.datasets_dir = path_config.datasets
        self.processing_dir = path_config.processing
        self.results_dir = path_config.results

        self.result_workflow_dir = os.path.join(
            self.results_dir, self.city, self.wflow_name
        )
        self.processing_workflow_dir = os.path.join(
            self.processing_dir, self.city, self.wflow_name
        )
        if self.override_files: 
            self._remove_dir(self.processing_workflow_dir)
        self._ensure_dir(self.result_workflow_dir)
        self._ensure_dir(self.processing_workflow_dir)

    @abstractmethod
    def run(self) -> None:
        pass

    def _ensure_dir(self, path: str | Path) -> None:
        p = Path(path)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.exception("Failed to ensure directory exists: %s", p)
            raise

    def _remove_dir(self, dir_path: str | Path) -> None:
        p = Path(dir_path)
        if p.exists():
            if not p.is_dir():
                logger.warning("Path exists but is not a directory, skipping removal: %s", p)
                return
            try:
                shutil.rmtree(p)
            except Exception:
                logger.exception("Failed to remove directory: %s", p)
                raise
