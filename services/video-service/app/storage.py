import io
import uuid
from typing import Optional

import boto3
from botocore.client import Config

from shared.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


BUCKET = "videos"


def ensure_bucket():
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=BUCKET)
    except Exception:
        client.create_bucket(Bucket=BUCKET)


def upload_video(file_data: bytes, filename: str, content_type: str) -> str:
    ensure_bucket()
    key = f"raw/{uuid.uuid4()}/{filename}"
    get_s3_client().put_object(
        Bucket=BUCKET,
        Key=key,
        Body=io.BytesIO(file_data),
        ContentType=content_type,
    )
    return key


def get_presigned_url(key: str, expires: int = 3600) -> str:
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=expires,
    )
