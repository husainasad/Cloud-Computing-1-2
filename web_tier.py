from fastapi import FastAPI, UploadFile
from fastapi.responses import PlainTextResponse
import boto3
import base64
import json

app = FastAPI()

AWS_REGION = 'us-east-1'
REQUEST_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/223420481310/1225380117-req-queue'
RESPONSE_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/223420481310/1225380117-resp-queue'

sqs_client = boto3.client('sqs', region_name=AWS_REGION)

@app.post("/", response_class=PlainTextResponse)
async def get_app_result(inputFile: UploadFile):
    
    file_content = await inputFile.read()
    image_name = inputFile.filename.split('.')[0]
    image_encoded = base64.b64encode(file_content).decode('utf-8')

    message = {
        'image_name': image_name,
        'image_encoded': image_encoded
    }

    message_json = json.dumps(message)

    send_response = sqs_client.send_message(
        QueueUrl=REQUEST_QUEUE_URL,
        MessageBody= message_json
    )

    # print(f"Message sent to Request SQS with MessageId: {send_response['MessageId']}")

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

        # print('Received image output from SQS')

        # Delete received message from queue
        receipt_handle = message['ReceiptHandle']
        sqs_client.delete_message(
            QueueUrl=RESPONSE_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        # print('Deleted message')
        
        # print(app_result)
        return app_result