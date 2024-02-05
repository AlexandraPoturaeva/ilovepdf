from pydantic import BaseModel, HttpUrl


class FileInfo(BaseModel):
    filename: str = ''
    storage_url: HttpUrl | str = ''
    storage_filename: str = ''
    pdf_api_server_filename: str = ''
