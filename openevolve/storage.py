"""Persistence helpers for program/checkpoint storage."""

import json
import logging
import os
from typing import Any, Dict, Iterable, Optional

logger = logging.getLogger(__name__)


class ProgramStorage:
    """Filesystem storage adapter for program database artifacts."""

    PROGRAMS_DIRNAME = "programs"
    METADATA_FILENAME = "metadata.json"

    def ensure_base_path(self, base_path: str) -> None:
        os.makedirs(base_path, exist_ok=True)

    def save_program(self, base_path: str, program_id: str, payload: Dict[str, Any]) -> str:
        programs_dir = os.path.join(base_path, self.PROGRAMS_DIRNAME)
        os.makedirs(programs_dir, exist_ok=True)
        program_path = os.path.join(programs_dir, f"{program_id}.json")
        with open(program_path, "w") as handle:
            json.dump(payload, handle)
        return program_path

    def save_metadata(self, base_path: str, metadata: Dict[str, Any]) -> str:
        self.ensure_base_path(base_path)
        metadata_path = os.path.join(base_path, self.METADATA_FILENAME)
        with open(metadata_path, "w") as handle:
            json.dump(metadata, handle)
        return metadata_path

    def load_metadata(self, base_path: str) -> Optional[Dict[str, Any]]:
        metadata_path = os.path.join(base_path, self.METADATA_FILENAME)
        if not os.path.exists(metadata_path):
            return None
        with open(metadata_path, "r") as handle:
            return json.load(handle)

    def iter_program_payloads(self, base_path: str) -> Iterable[Dict[str, Any]]:
        programs_dir = os.path.join(base_path, self.PROGRAMS_DIRNAME)
        if not os.path.exists(programs_dir):
            return
        for program_file in os.listdir(programs_dir):
            if not program_file.endswith(".json"):
                continue
            program_path = os.path.join(programs_dir, program_file)
            try:
                with open(program_path, "r") as handle:
                    yield json.load(handle)
            except Exception as exc:
                logger.warning("Failed to load program file %s: %s", program_file, exc)
