"""
python manage.py setup_r2_cors

Sets the correct CORS policy on your Cloudflare R2 bucket so that:
  - Videos stream correctly in the browser (Range requests work)
  - Thumbnails load from any origin
  - Signed URLs work for video playback

Run this ONCE after creating your R2 bucket.
Requires CF_R2_* env vars to be set.
"""
import json
from django.core.management.base import BaseCommand
from django.conf import settings


CORS_RULES = [
    {
        "AllowedOrigins": ["*"],
        "AllowedMethods": ["GET", "HEAD"],
        "AllowedHeaders": [
            "Range",             # required for video seeking
            "Content-Type",
            "Authorization",
            "x-amz-date",
            "x-amz-content-sha256",
        ],
        "ExposeHeaders": [
            "Content-Length",
            "Content-Range",     # required for video seeking
            "Accept-Ranges",
            "ETag",
        ],
        "MaxAgeSeconds": 86400,
    }
]


class Command(BaseCommand):
    help = "Apply CORS rules to Cloudflare R2 bucket for video streaming"

    def handle(self, *args, **options):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            self.stdout.write(self.style.ERROR("boto3 not installed. Run: pip install boto3"))
            return

        endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "")
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "")
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "")

        if not all([endpoint, bucket, access_key, secret_key]) or "dummy" in endpoint:
            self.stdout.write(self.style.ERROR(
                "R2 credentials not set. Fill CF_R2_* env vars first."
            ))
            self.stdout.write("\nManual setup (Cloudflare Dashboard):")
            self.stdout.write("  1. Go to R2 → your bucket → Settings → CORS Policy")
            self.stdout.write("  2. Paste this JSON:\n")
            self.stdout.write(json.dumps(CORS_RULES, indent=2))
            return

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

        try:
            client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration={"CORSRules": CORS_RULES},
            )
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ CORS rules applied to bucket: {bucket}\n"
                f"\nVideos will now stream correctly in browsers.\n"
                f"Range requests (video seeking) are enabled.\n"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed: {e}"))
            self.stdout.write("\nManual fallback — paste this in Cloudflare Dashboard:")
            self.stdout.write("R2 → your bucket → Settings → CORS Policy")
            self.stdout.write(json.dumps(CORS_RULES, indent=2))
