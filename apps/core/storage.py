"""
apps/core/storage.py

Custom Cloudflare R2 storage backends:
- PublicMediaStorage  → thumbnails, images (publicly readable)
- PrivateVideoStorage → video files (signed URL, expires in 1 hour)
"""
import boto3
from botocore.config import Config
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class PublicMediaStorage(S3Boto3Storage):
    """For images, thumbnails — publicly accessible via R2 public domain."""
    location = "media"
    file_overwrite = False
    default_acl = None  # R2 uses bucket-level public access, not per-object ACL

    def url(self, name):
        """Return public CDN URL directly."""
        public_domain = getattr(settings, "CF_R2_PUBLIC_DOMAIN", None)
        if public_domain:
            return f"https://{public_domain}/{self.location}/{name}"
        return super().url(name)


class PrivateVideoStorage(S3Boto3Storage):
    """
    For video files — generates pre-signed URLs valid for 1 hour.
    Videos are stored in a private/ prefix, not publicly readable.
    """
    location = "private"
    file_overwrite = False
    default_acl = None
    custom_domain = None  # Never expose direct URL — always use signed

    def url(self, name, expire=3600):
        """Generate a pre-signed URL valid for `expire` seconds (default 1hr)."""
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        return s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": f"{self.location}/{name}",
            },
            ExpiresIn=expire,
        )


def get_video_storage():
    """Return the correct storage backend based on environment."""
    if getattr(settings, "USE_R2_STORAGE", False):
        return PrivateVideoStorage()
    # Local dev: use default FileSystemStorage
    from django.core.files.storage import default_storage
    return default_storage
