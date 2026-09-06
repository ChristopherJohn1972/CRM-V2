import hmac
import hashlib
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings


def sign_key(storage_key: str, expires_epoch: int) -> str:
    message = f"{storage_key}:{expires_epoch}".encode("utf-8")
    digest = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return digest


def verify_key_sig(storage_key: str, expires_epoch: int, signature: str) -> bool:
    expected = sign_key(storage_key, expires_epoch)
    return hmac.compare_digest(expected, signature)


class ObjectStorage(ABC):
    @abstractmethod
    def put(self, storage_key: str, data: bytes, content_type: str = None) -> None:
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        pass

    @abstractmethod
    def download_url(self, storage_key: str, expires: int) -> str:
        pass

    def upload_url(self, storage_key: str, expires: int, content_type: str = None):
        raise NotImplementedError


class LocalFilesystemStorage(ObjectStorage):
    def __init__(self, root: str):
        self.root = Path(root)

    def _path(self, storage_key: str) -> Path:
        return self.root / Path(storage_key)

    def put(self, storage_key: str, data: bytes, content_type: str = None):
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def delete(self, storage_key: str):
        try:
            self._path(storage_key).unlink(missing_ok=True)
        except OSError:
            pass

    def download_url(self, storage_key: str, expires: int) -> str:
        exp = int(time.time()) + expires
        sig = sign_key(storage_key, exp)
        from urllib.parse import quote

        return (
            f"/api/documents/serve?key={quote(storage_key)}&expires={exp}&sig={sig}"
        )

    def read(self, storage_key: str) -> bytes:
        return self._path(storage_key).read_bytes()


class S3Storage(ObjectStorage):
    def __init__(self, bucket: str, region: str, ttl: int):
        import boto3

        self.bucket = bucket
        self.region = region
        self.ttl = ttl
        self.client = boto3.client("s3", region_name=region)

    def put(self, storage_key: str, data: bytes, content_type: str = None):
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=storage_key, Body=data, **extra)

    def delete(self, storage_key: str):
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)

    def download_url(self, storage_key: str, expires: int) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires,
        )

    def upload_url(self, storage_key: str, expires: int, content_type: str = None):
        params = {"Bucket": self.bucket, "Key": storage_key}
        if content_type:
            params["ContentType"] = content_type
        return self.client.generate_presigned_url(
            "put_object", Params=params, ExpiresIn=expires
        )


def build_storage(settings_module=settings):
    backend = settings_module.STORAGE_BACKEND
    if backend == "s3":
        if not settings_module.S3_BUCKET:
            raise RuntimeError("CRM_S3_BUCKET must be set when STORAGE_BACKEND=s3")
        return S3Storage(
            settings_module.S3_BUCKET,
            settings_module.S3_REGION,
            settings_module.S3_PRESIGNED_URL_TTL,
        )
    return LocalFilesystemStorage(settings_module.STORAGE_ROOT)


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        _storage = build_storage()
    return _storage