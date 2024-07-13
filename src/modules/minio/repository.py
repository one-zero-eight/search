from minio import Minio
from minio.error import S3Error

from src.api.logging_ import logger
from src.config import settings
from src.modules.minio.schemas import MoodleFileObject
from src.storages.minio import minio_client


class MinioRepository:
    def __init__(self, minio_client: Minio):
        self.minio_client = minio_client

    def get_moodle_objects(self) -> list[MoodleFileObject]:
        try:
            moodle_objects = []
            # List all objects with the "moodle/" prefix recursively
            objects = self.minio_client.list_objects(
                bucket_name=settings.minio.bucket, prefix="moodle/", recursive=True
            )
            for obj in objects:
                parts = obj.object_name.split("/")
                if len(parts) >= 4:
                    try:
                        course_id = int(parts[1])
                        module_id = int(parts[2])
                        filename = parts[3]

                        moodle_object = MoodleFileObject(course_id=course_id, module_id=module_id, filename=filename)
                        moodle_objects.append(moodle_object)
                    except (ValueError, S3Error) as e:
                        logger.error(f"Error processing object {obj.object_name}: {e}")
            return moodle_objects
        except S3Error as e:
            logger.error(f"An error occurred while listing Moodle objects: {e}")
            return []


minio_repository: MinioRepository = MinioRepository(minio_client)
