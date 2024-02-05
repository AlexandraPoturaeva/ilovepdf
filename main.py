from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile, Request
from ilovepdf_api import IlovepdfAPI
import httpx
import os

load_dotenv()
ilovepdf_api_public_key = os.environ.get('ILOVEPDF_PUBLIC_KEY')


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.requests_client = httpx.AsyncClient(verify=False)
    yield
    await app.requests_client.aclose()


app = FastAPI(lifespan=lifespan)
api = IlovepdfAPI(public_key=ilovepdf_api_public_key)


@app.post("/pdf_to_jpg")
async def pdf_to_jpg(
        request: Request,
        files: list[UploadFile],
        mode: str = Form(
            description="Accepted values:"
                        "pages=Convert every PDF page to a JPG image,"
                        "extract=extract all PDF's embedded images "
                        "to separate JPG image",
            default='pages',
            pattern='^(pages|extract)$',
        )):
    output_file_url = await api.process(
        tool='pdfjpg',
        extra_parameters={'pdfjpg_mode': mode},
        files=files,
        request=request
    )
    return {'output_file_url': output_file_url}
