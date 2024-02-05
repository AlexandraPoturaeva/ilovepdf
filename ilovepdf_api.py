import asyncio
import os
from io import BytesIO
from fastapi import Request, HTTPException, UploadFile
from utils import validate_pdf_file, api_error_handler
from yandex_s3 import YandexS3


storage = YandexS3(bucket_name=os.environ.get('YANDEX_S3_BUCKET_NAME'))


class IlovepdfAPI:
    def __init__(self, public_key):
        self.public_key = public_key
        self.api_version = 'v1'
        self.start_server = 'api.ilovepdf.com'
        self.headers = None
        self.requests_client = None

    def _set_headers(self, token):
        self.headers = {"Authorization": "Bearer " + token}

    async def _auth(self):
        url = 'https://' + self.start_server + '/' + self.api_version + '/auth'
        payload = {"public_key": self.public_key}
        response = await self.requests_client.post(url=url, data=payload)
        api_error_handler(response)
        self._set_headers(token=response.json()['token'])

    async def _start(self, request: Request, tool: str):
        self.requests_client = request.app.requests_client
        await self._auth()
        url = (
                'https://' +
                self.start_server + '/' +
                self.api_version + '/start/' +
                tool
        )
        response = await self.requests_client.get(
            url=url,
            headers=self.headers
        )
        api_error_handler(response)

        return response.json()

    async def process(self, files, tool, request, extra_parameters):
        tasks = [asyncio.to_thread(
            validate_pdf_file,
            file=file
        ) for file in files]
        await asyncio.gather(*tasks)
        tool = Tool(self.public_key, tool=tool)
        result = await tool.process_files(files, request, extra_parameters)
        return result


class Tool(IlovepdfAPI):
    def __init__(self, public_key, tool):
        super().__init__(public_key)
        self.tool = tool
        self.files = []
        self.working_server = ''
        self.server_url = ''
        self.task = ''
        self.status = ''
        self.output_file_url = ''
        self.output_file_name = ''
        self.extra_parameters = None

    def _set_server_url(self, working_server: str):
        self.server_url = (
                'https://' +
                working_server + '/' +
                self.api_version + '/'
        )

    def _files_list(self):
        files_list = [
            {
                'server_filename': file.pdf_api_server_filename,
                'filename': file.filename
             } for file in self.files
        ]
        return files_list

    async def process_files(self, files, request, extra_parameters):
        self.extra_parameters = extra_parameters
        self.files = await storage(files)
        task_info = await super()._start(request=request, tool=self.tool)
        self._set_server_url(task_info['server'])
        self.task = task_info['task']

        tasks = [asyncio.create_task(
            self._upload(file=file)
        ) for file in self.files]

        await asyncio.gather(*tasks)

        await self._execute()

        if self.status == 'TaskSuccess':
            await self._download()

            try:
                return self.output_file_url
            finally:
                await self._delete_current_task()
        else:
            raise HTTPException(500)

    async def _upload(self, file):
        url = self.server_url + 'upload'
        payload = {"task": self.task, 'cloud_file': file.storage_url}
        response = await self.requests_client.post(
            url=url,
            headers=self.headers,
            data=payload
        )
        api_error_handler(response)
        file.pdf_api_server_filename = response.json()['server_filename']

    async def _execute(self):
        url = self.server_url + 'process'
        payload = {
            'task': self.task,
            'tool': self.tool,
            'files': self._files_list()
        }
        if self.extra_parameters:
            payload.update(self.extra_parameters)

        response = await self.requests_client.post(
            url=url,
            headers=self.headers,
            json=payload
        )
        api_error_handler(response)
        self.status = response.json()['status']
        self.output_file_name = response.json()['download_filename']

    async def _download(self):
        url = self.server_url + 'download/' + self.task
        response = await self.requests_client.get(
            url=url,
            headers=self.headers
        )
        api_error_handler(response)
        file = UploadFile(
            file=BytesIO(response.content),
            filename=self.output_file_name
        )
        result_file = await storage.upload(file=file)
        self.output_file_url = result_file.storage_url

    async def _delete_current_task(self):
        url = self.server_url + 'task/' + self.task
        await self.requests_client.delete(url=url, headers=self.headers)
