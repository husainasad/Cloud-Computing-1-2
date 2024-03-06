from fastapi import FastAPI, UploadFile
from fastapi.responses import PlainTextResponse
import httpx

app = FastAPI()

APP_URL = 'http://127.0.0.1:5000/'

# async def fetch_app(input_file):
#     async with httpx.AsyncClient() as client:
#         app_response = await client.post(APP_URL, files={"inputFile": (input_file.filename, input_file.file)})
#     return app_response.text

@app.post("/", response_class=PlainTextResponse)
async def get_app_result(inputFile: UploadFile):
    # app_result = await fetch_app(inputFile)

    async with httpx.AsyncClient() as client:
        app_result = await client.post(APP_URL, files={"inputFile": (inputFile.filename, inputFile.file)})
    # return f"{app_result}"
    return app_result.text