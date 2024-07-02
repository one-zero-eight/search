from typing import Any
from minio import Minio
from minio.error import S3Error
from src.api.logging_ import logger
from src.storages.minio import minio_client as client


class MinioRepository:
    def __init__(self, minio_client: Minio):
        self.minio_client = minio_client

    def get_moodle_objects(self) -> list[dict[str, Any]]:
        try:
            moodle_objects = []
            # List all objects with the "moodle/" prefix recursively
            objects = self.minio_client.list_objects(bucket_name="search", prefix="moodle/", recursive=True)
            for obj in objects:
                parts = obj.object_name.split("/")
                if len(parts) >= 4:
                    try:
                        course_id = int(parts[1])
                        module_id = int(parts[2])
                        filename = parts[3]

                        # Retrieve the object metadata
                        object_stat = self.minio_client.stat_object("search", obj.object_name)

                        moodle_object = {
                            "course_id": course_id,
                            "module_id": module_id,
                            "filename": filename,
                            "minio_data": {
                                "size": object_stat.size,
                                "last_modified": str(object_stat.last_modified),
                                "object_name": obj.object_name,
                                "metadata": str(object_stat.metadata),
                            },
                        }
                        moodle_objects.append(moodle_object)
                    except (ValueError, S3Error) as e:
                        logger.error(f"Error processing object {obj.object_name}: {e}")
            return moodle_objects
        except S3Error as e:
            logger.error(f"An error occurred while listing Moodle objects: {e}")
            return []


minio_repository: MinioRepository = MinioRepository(client)
