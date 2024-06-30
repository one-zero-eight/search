from typing import List, Dict
from minio import Minio
from minio.error import S3Error
from src.api.logging_ import logger
from src.storages.minio import minio_client as client


class MinioRepository:
    def __init__(self, minio_client: Minio):
        self.minio_client = minio_client

    def get_moodle_objects(self) -> List[Dict[str, any]]:
        try:
            # List all objects with the "moodle/" prefix
            objects = self.minio_client.list_objects(bucket_name="search", prefix="moodle/")
            moodle_objects = []
            for obj in objects:
                # would it work like this?
                parts = obj.object_name.split("/")
                if len(parts) >= 3:
                    course_id = int(parts[1])
                    module_id = int(parts[2])
                    filename = parts[-1]
                    moodle_object = {
                        "course_id": course_id,
                        "module_id": module_id,
                        "filename": filename,
                        "minio_data": obj,
                    }
                    moodle_objects.append(moodle_object)
            return moodle_objects
        except S3Error as e:
            logger.error(f"An error occurred while listing Moodle objects: {e}")
            return []


minio_repository: MinioRepository = MinioRepository(client)
