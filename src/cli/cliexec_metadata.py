import logging
import os
from typing import Dict, List, Any

import common.const
from geoserver import metadata

logging.basicConfig(level=logging.INFO, format=common.const.LOGGING_FORMAT)
logger = logging.getLogger(__name__)


class CliExecMetadata:

    def __init__(self):
        pass

    def initialize(
            self,
            database_dir: str) -> bool:
        """
        Create a temperature data base as demo data

        TODO: intended to be replaced with more reusable database stuff
            at a later date

        returns true id db created, returns false if db already exists
        """
        if os.path.exists(database_dir):
            logger.info(f"Database already exists at location {database_dir}")
            return False
        os.makedirs(database_dir)
        return True

    def add_meta(
            self,
            database_dir: str,
            dataset_name: str,
            description: str,
            key_columns: Dict[str ,str],
            value_columns: Dict[str, str],
            dataset_type: str
    ) -> str:
        meta = metadata.MetadataDB(database_dir)
        return meta.add_metadata_entry(
            dataset_name,
            description,
            key_columns,
            value_columns,
            dataset_type
        )

    def show_meta(
            self,
            database_dir: str
    ) -> List[Dict[str, Any]]:
        meta = metadata.MetadataDB(database_dir)
        return meta.show_meta()
