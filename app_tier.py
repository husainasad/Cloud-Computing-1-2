from Resources.model.face_recognition import face_match
import boto3, base64, json, asyncio, os, signal, logging, sys

with open('config.json') as f:
    config = json.load(f)

AWS_REGION = config['AWS_REGION']
REQUEST_QUEUE_URL = config['REQUEST_QUEUE_URL']
RESPONSE_QUEUE_URL = config['RESPONSE_QUEUE_URL']
IN_BUCKET = config['IN_BUCKET']
OUT_BUCKET = config['OUT_BUCKET']
DATA_PT_PATH = config['DATA_PT_PATH']

sts_client = boto3.client('sts')

session = boto3.Session()

sqs_client = session.client('sqs', region_name=AWS_REGION)

s3_client = session.client('s3')

terminate_flag = False

def signal_handler(signum, frame):
    global terminate_flag
    terminate_flag = True
    logging.info("Termination signal received. Waiting for current request to complete...")
    sys.exit(0)
    
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def get_data_From_sqs(message_body):
    image_name = message_body['image_name']
    image_encoded = message_body['image_encoded']
    image_data = base64.b64decode(image_encoded)

    return image_name, image_data

async def upload_to_s3_and_delete_msg(image_name, image_data, model_result, receipt_handle):
    s3_client.put_object(Body=image_data, Bucket=IN_BUCKET, Key=image_name + '.jpg')
    s3_client.put_object(Body=model_result, Bucket=OUT_BUCKET, Key=image_name)

    sqs_client.delete_message(
        QueueUrl=REQUEST_QUEUE_URL,
        ReceiptHandle=receipt_handle
    )

    output_msg = f'{image_name}:{model_result}'

    sqs_client.send_message(
        QueueUrl=RESPONSE_QUEUE_URL,
        MessageBody=(
            output_msg
        )
    )

async def process_img(image_data):
    try:
        with open('temp.jpg', 'wb') as f:
            f.write(image_data)
        result = face_match('temp.jpg', DATA_PT_PATH)[0]
        return f'{result}'
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        os.remove('temp.jpg')
    

async def process_msg():
    while not terminate_flag:
        receive_response = sqs_client.receive_message(
            QueueUrl=REQUEST_QUEUE_URL,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=10,
            WaitTimeSeconds=0
        )

        if 'Messages' in receive_response:
            message = receive_response['Messages'][0]
            
            message_body = json.loads(message['Body'])

            image_name, image_data = await get_data_From_sqs(message_body)

            model_result = await process_img(image_data)

            await upload_to_s3_and_delete_msg(image_name, image_data, model_result, message['ReceiptHandle'])

            if terminate_flag:
                break

if __name__ == "__main__":
    logging.basicConfig(filename='app_server.log', level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_msg())