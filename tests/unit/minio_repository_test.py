from datetime import timedelta
from unittest.mock import MagicMock, patch

from minio.error import S3Error


def test_get_moodle_objects_success(minio_repository, mock_minio_client):
    correct_obj1 = MagicMock()
    correct_obj1.object_name = "moodle/1/2/file1.pdf"

    correct_obj2 = MagicMock()
    correct_obj2.object_name = "moodle/11/22/file2.pdf"

    wrong_obj1 = MagicMock()
    wrong_obj1.object_name = "moodle/blabla/fa/file.pdf"

    wrong_obj2 = MagicMock()
    wrong_obj2.object_name = "moodle/incomplete/path"

    mock_minio_client.list_objects.return_value = [correct_obj1, correct_obj2, wrong_obj1, wrong_obj2]

    result = minio_repository.get_moodle_objects()

    assert len(result) == 2

    assert result[0].course_id == 1
    assert result[0].module_id == 2
    assert result[0].filename == "file1.pdf"

    assert result[1].course_id == 11
    assert result[1].module_id == 22
    assert result[1].filename == "file2.pdf"

    mock_minio_client.list_objects.assert_called_once_with(
        bucket_name=minio_repository.minio_client.bucket, prefix="moodle/", recursive=True
    )


def test_get_moodle_objects_s3_error(minio_repository, mock_minio_client):
    err = S3Error(
        code="test", message="test", resource="moodle/", request_id="43242", host_id="43242", response=MagicMock()
    )
    mock_minio_client.list_objects.side_effect = err

    result = minio_repository.get_moodle_objects()

    assert result == []
    mock_minio_client.list_objects.assert_called_once()


def test_get_presigned_url_moodle(minio_repository, mock_minio_client):
    course_id = 1
    module_id = 2
    filename = "file.pdf"
    expected_obj_name = f"moodle/{course_id}/{module_id}/{filename}"

    with patch("src.modules.minio.repository.content_to_minio_object") as mock_content_to_obj:
        mock_content_to_obj.return_value = expected_obj_name

        mock_minio_client.presigned_get_object.return_value = "https://someurl/" + expected_obj_name

        result = minio_repository.get_presigned_url_moodle(course_id, module_id, filename)

        assert result == "https://someurl/" + expected_obj_name

        mock_content_to_obj.assert_called_once_with(course_id, module_id, filename)
        mock_minio_client.presigned_get_object.assert_called_once_with(
            "test_bucket", expected_obj_name, expires=timedelta(days=1)
        )


def test_put_presigned_url_moodle(minio_repository, mock_minio_client):
    course_id = 1
    module_id = 2
    filename = "file.pdf"
    expected_obj_name = f"moodle/{course_id}/{module_id}/{filename}"

    with patch("src.modules.minio.repository.content_to_minio_object") as mock_content_to_obj:
        mock_content_to_obj.return_value = expected_obj_name

        mock_minio_client.presigned_put_object.return_value = "https://someurl/" + expected_obj_name

        result = minio_repository.put_presigned_url_moodle(course_id, module_id, filename)

        assert result == "https://someurl/" + expected_obj_name
        mock_content_to_obj.assert_called_once_with(course_id, module_id, filename)
        mock_minio_client.presigned_put_object.assert_called_once_with(
            "test_bucket", expected_obj_name, expires=timedelta(days=1)
        )
