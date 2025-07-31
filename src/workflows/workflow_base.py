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

from pathlib import Path
from abc import ABC, abstractmethod
from multiprocessing import Pool, cpu_count


class BaseWorkflow(ABC):
    def __init__(self, city, bbox_4326, workflow_name: str):
        self.bbox = bbox_4326
        self.workflow_name = workflow_name
        self.num_processes = cpu_count()

    @abstractmethod
    def run(self):
        pass

    def _ensure_dir(self, path):
        os.makedirs(path, exist_ok=True)
