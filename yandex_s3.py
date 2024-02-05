import asyncio
import boto3
import os
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException
from functools import cache
from schemas import FileInfo

load_dotenv()


class YandexS3:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    @property
    @cache
    def client(self):
        key_id = os.environ.get('YANDEX_S3_ACCESS_KEY_ID')
        access_key = os.environ.get('YANDEX_S3_SECRET_ACCESS_KEY')
        region_name = os.environ.get('YANDEX_S3_DEFAULT_REGION')
        return boto3.client(
            service_name='s3',
            endpoint_url='https://storage.yandexcloud.net',
            region_name=region_name,
            aws_access_key_id=key_id,
            aws_secret_access_key=access_key
        )

    async def __call__(
            self,
            files: list[UploadFile]
    ):
        return await self._multi_upload(files=files)

    async def upload(self, file: UploadFile) -> FileInfo:
        file_info = FileInfo()
        file_info.filename = file.filename
        file_ext = os.path.splitext(file.filename)[1]
        file_info.storage_filename = str(uuid4()) + file_ext

        try:
            await asyncio.to_thread(
                self.client.upload_fileobj,
                file.file,
                self.bucket_name,
                file_info.storage_filename
            )
            file_info.storage_url = (
                f"https://storage.yandexcloud.net/"
                f"{self.bucket_name}/"
                f"{file_info.storage_filename}"
            )
        except Exception as err:
            raise HTTPException(500, detail=str(err))

        return file_info

    async def _multi_upload(self, files: list[UploadFile]):
        tasks = [asyncio.create_task(self.upload(file=file)) for file in files]
        return await asyncio.gather(*tasks)
