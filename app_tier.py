from Resources.model.face_recognition import face_match
from fastapi import FastAPI, UploadFile
from fastapi.responses import PlainTextResponse

app = FastAPI()

data_pt_path = './Resources/model/data.pt'

async def process_img(input_file):
    try:
        img_content = await input_file.read()
        with open("temp_image.jpg", "wb") as f:
            f.write(img_content)
        result = face_match("temp_image.jpg", data_pt_path)[0]
        img_file_name = input_file.filename.split('.')[0]
        return f"{img_file_name}:{result}"
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/", response_class=PlainTextResponse)
async def get_img_result(inputFile: UploadFile):
    output = await process_img(inputFile)
    return output