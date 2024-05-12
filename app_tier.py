from Resources.model import facenet_pytorch
from Resources.model.face_recognition import face_match
import aioboto3, base64, json, asyncio, os, signal, logging, sys

with open('config.json') as f:
    config = json.load(f)

AWS_REGION = config['AWS_REGION']
REQUEST_QUEUE_URL = config['REQUEST_QUEUE_URL']
RESPONSE_QUEUE_URL = config['RESPONSE_QUEUE_URL']
IN_BUCKET = config['IN_BUCKET']
OUT_BUCKET = config['OUT_BUCKET']
DATA_PT_PATH = config['DATA_PT_PATH']

session = aioboto3.Session()

terminate_flag = False

def signal_handler(signum, frame):
    global terminate_flag
    terminate_flag = True
    logging.info("Termination signal received. Waiting for current request to complete...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def get_data_From_msg(message_body):
    image_name = message_body['image_name']
    image_encoded = message_body['image_encoded']
    image_data = base64.b64decode(image_encoded)

    return image_name, image_data

async def upload_to_s3_sqs_and_delete_msg(image_name, image_data, model_result, receipt_handle):
    async with session.client('s3') as s3_client:
        await s3_client.put_object(Body=image_data, Bucket=IN_BUCKET, Key=image_name + '.jpg')
        await s3_client.put_object(Body=model_result, Bucket=OUT_BUCKET, Key=image_name)

    async with session.client('sqs', region_name=AWS_REGION) as sqs_client:
        await sqs_client.delete_message(
            QueueUrl=REQUEST_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )

    output_msg = f'{image_name}:{model_result}'
    message = {
        'image_name': image_name,
        'image_result': output_msg
    }
    message_json = json.dumps(message)

    async with session.client('sqs', region_name=AWS_REGION) as sqs_client:
        await sqs_client.send_message(
            QueueUrl=RESPONSE_QUEUE_URL,
            MessageBody=message_json
        )

async def process_img(image_name, image_data):
    try:
        img_file_name = image_name+'.jpg'
        with open(img_file_name, 'wb') as f:
            f.write(image_data)
        result = face_match(img_file_name, DATA_PT_PATH)[0]
        return f'{result}'
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        os.remove(img_file_name)

async def process_msg():
    while not terminate_flag:
        async with session.client('sqs', region_name=AWS_REGION) as sqs_client:
            receive_response = await sqs_client.receive_message(
                QueueUrl=REQUEST_QUEUE_URL,
                AttributeNames=['SentTimestamp'],
                MaxNumberOfMessages=1,
                MessageAttributeNames=['All'],
                VisibilityTimeout=30,
                WaitTimeSeconds=1
            )

            if 'Messages' in receive_response:
                message = receive_response['Messages'][0]
                message_body = json.loads(message['Body'])
                image_name, image_data = await get_data_From_msg(message_body)
                model_result = await process_img(image_name, image_data)
                await upload_to_s3_sqs_and_delete_msg(image_name, image_data, model_result, message['ReceiptHandle'])
                if terminate_flag:
                    break

if __name__ == "__main__":
    logging.basicConfig(filename='app_server.log', level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_msg())