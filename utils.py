from fastapi import UploadFile, HTTPException
from pypdf import PdfReader


def validate_pdf_file(file: UploadFile):
    if file.content_type != 'application/pdf':
        raise HTTPException(
            406,
            detail=f'Invalid document type of {file.filename}')

    if PdfReader(file.file).is_encrypted:
        raise HTTPException(
            406,
            detail=f'{file.filename}: remove password and try again')

    file.file.seek(0)


def api_error_handler(response):
    if response.status_code != 200:
        print(response.json())
        raise HTTPException(
            status_code=500,
            detail='Something went wrong with ILovePDF API'
        )
    return 'No api errors'
