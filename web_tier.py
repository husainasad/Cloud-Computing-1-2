from fastapi import FastAPI, UploadFile
from fastapi.responses import PlainTextResponse
import boto3, base64, json, asyncio

app = FastAPI()

with open('config.json') as f:
    config = json.load(f)

AWS_REGION = config['AWS_REGION']
REQUEST_QUEUE_URL = config['REQUEST_QUEUE_URL']
RESPONSE_QUEUE_URL = config['RESPONSE_QUEUE_URL']

sts_client = boto3.client('sts')

session = boto3.Session()

sqs_client = session.client('sqs', region_name=AWS_REGION)
    
async def process_request(file_content, image_name):
    image_encoded = base64.b64encode(file_content).decode('utf-8')

    message = {
        'image_name': image_name,
        'image_encoded': image_encoded
    }

    message_json = json.dumps(message)

    sqs_client.send_message(
        QueueUrl=REQUEST_QUEUE_URL,
        MessageBody=message_json
    )

async def process_response():
    receive_response = sqs_client.receive_message(
        QueueUrl=RESPONSE_QUEUE_URL,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=20
    )

    if 'Messages' in receive_response:
        message = receive_response['Messages'][0]

        app_result = message['Body']

        receipt_handle = message['ReceiptHandle']
        sqs_client.delete_message(
            QueueUrl=RESPONSE_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        return app_result

@app.post("/", response_class=PlainTextResponse)
async def get_app_result(inputFile: UploadFile):
    
    file_content = await inputFile.read()
    image_name = inputFile.filename.split('.')[0]

    request_task = asyncio.ensure_future(process_request(file_content, image_name))

    response_task = asyncio.ensure_future(process_response())

    await asyncio.gather(request_task, response_task)

    response = response_task.result()

    return response