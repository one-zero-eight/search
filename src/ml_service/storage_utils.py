from minio import Minio
from minio.error import S3Error


def get_minio_client(endpoint, access_key, secret_key, secure=True):
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def get_presigned_url(client, bucket, filename, expires=3600):
    """
    Generate a presigned URL for downloading a file from Minio.
    """
    try:
        url = client.presigned_get_object(bucket, filename, expires=expires)
        return url
    except S3Error as err:
        print(f"Error getting presigned url: {err}")
        return None
