import boto3
from botocore.exceptions import ClientError
from SF import settings
import io
import mimetypes


class S3BucketHelper:
    """
    This class is a helper class that provides utility functions to work with Amazon Simple Storage Service (S3).
    The functions include uploading and deleting objects (files) to and from a specified S3 bucket, and checking if a
    specified folder exists within the bucket.
    """

    def __init__(self, foldername=None, path=None):
        self.s3_resource = boto3.client(
            "s3",
            region_name=settings.AWS_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
        )
        self.s3_foldername = foldername
        self.path = path

    def upload_to_s3(self, creative_name):
        """
        Upload a file to the S3 bucket.
        """
        try:
            with open(self.path, "rb") as f:
                content_type = mimetypes.guess_type(creative_name)[0]
                self.s3_resource.upload_fileobj(
                    io.BytesIO(f.read()),
                    settings.AWS_BUCKET_NAME,
                    Key=self.s3_foldername + "/" + creative_name,
                    ExtraArgs={
                        "ACL": "public-read",
                        "ContentType": content_type,
                        "ContentDisposition": "inline",
                    },
                )
        except ClientError as e:
            return False, repr(e)

        return True, None

    def does_exist_creative_folder_in_s3(self, folder_name):
        """
        Check if the specified folder exists in the S3 bucket.
        """
        objects = self.s3_resource.list_objects_v2(
            Bucket=settings.AWS_BUCKET_NAME, Delimiter="/", Prefix=""
        )
        folders = objects.get("CommonPrefixes")

        folders_in_bucket = []
        if folders:
            for f in folders:
                folders_in_bucket.remove("/").append(f.get("Prefix").rstrip("/"))

        return folder_name in folders_in_bucket

    def delete_to_s3(self, creative_name):
        """
        Delete a file from the S3 bucket.
        """
        try:
            self.s3_resource.delete_object(
                Bucket=settings.AWS_BUCKET_NAME,
                Key=self.s3_foldername + "/" + creative_name,
            )
        except ClientError as e:
            return False, repr(e)

        return True, None

    def write_presigned_url(self, object_key, expiration=3600):
        """
        Generate a presigned URL to share an S3 object
        """
        response = self.s3_resource.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_BUCKET_NAME,
                "Key": object_key,
            },
            ExpiresIn=expiration,
        )
        return response

    def read_presigned_url(self, object_key, expiration=3600):
        """
        Generate a presigned URL to share an S3 object
        """
        response = self.s3_resource.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_BUCKET_NAME,
                "Key": object_key,
            },
            ExpiresIn=expiration,
        )
        return response
    
    def delete_object(self, Bucket, Key):
        try:
            self.s3_resource.delete_object(Bucket=Bucket, Key=Key)
            return True, None
        except Exception as e:
            return False, str(e)
