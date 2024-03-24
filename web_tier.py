from fastapi import FastAPI, UploadFile
from fastapi.responses import PlainTextResponse
import aioboto3, base64, json, asyncio, time

app = FastAPI()

with open('config.json') as f:
    config = json.load(f)

AWS_REGION = config['AWS_REGION']
REQUEST_QUEUE_URL = config['REQUEST_QUEUE_URL']
RESPONSE_QUEUE_URL = config['RESPONSE_QUEUE_URL']
IN_BUCKET = config['IN_BUCKET']
APP_INSTANCE_NAME = config['APP_INSTANCE_NAME']
MAX_SERVERS = config['MAX_SERVERS']

session = aioboto3.Session(region_name=AWS_REGION)

response_store = {}
pending_requests = False
last_request_time = time.time()

async def get_instances_with_tag(instance_name=APP_INSTANCE_NAME):
    async with session.client('ec2') as ec2_client:
        response = await ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [instance_name + '*']
                }
            ]
        )

        instances = [instance for reservation in response.get('Reservations', []) for instance in reservation.get('Instances', [])]
        return instances

async def scaling_controller():
    pending_requests = await get_sqs_length()
    servers_required = min(pending_requests, MAX_SERVERS)
    instances = await get_instances_with_tag()
    current_servers = len([instance for instance in instances if instance['State']['Name'] in ['running', 'pending']])

    if servers_required > current_servers:
        print("scaling up")
        await scale_up_servers(num=servers_required-current_servers)
    elif servers_required < current_servers:
        print("scaling down")
        await scale_down_servers(num=current_servers-servers_required)

async def scale_up_servers(instance_name=APP_INSTANCE_NAME, num=1):
    # await asyncio.sleep(1)
    instances = await get_instances_with_tag(instance_name)
    stopped_instances = [instance for instance in instances if instance['State']['Name'] in ['stopped']]

    if stopped_instances:
        instances_to_start = stopped_instances[:min(num, len(stopped_instances))]
        instance_ids = [instance['InstanceId'] for instance in instances_to_start]
        async with session.client('ec2') as ec2_client:
            await ec2_client.start_instances(InstanceIds=instance_ids)
    else:
        print("Cannot start any more instances")
        return

async def scale_down_servers(instance_name=APP_INSTANCE_NAME, num=1):
    # await asyncio.sleep(1)
    instances = await get_instances_with_tag(instance_name)
    running_instances = [instance for instance in instances if instance['State']['Name'] in ['running']]

    if running_instances:
        instances_to_stop = running_instances[:min(num, len(running_instances))]
        instance_ids = [instance['InstanceId'] for instance in instances_to_stop]
        async with session.client('ec2') as ec2_client:
            await ec2_client.stop_instances(InstanceIds=instance_ids)
    else:
        print("Cannot stop instances")
        return

async def get_sqs_length():
    async with session.client('sqs') as sqs_client:
        response = await sqs_client.get_queue_attributes(
            QueueUrl=REQUEST_QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        sqs_length = int(response['Attributes']['ApproximateNumberOfMessages'])
        print(f"SQS Length: {sqs_length}")
        return sqs_length

async def process_request(file_content, image_name):
    image_encoded = base64.b64encode(file_content).decode('utf-8')
    message = {
        'image_name': image_name,
        'image_encoded': image_encoded
    }
    message_json = json.dumps(message)
    async with session.client('sqs') as sqs_client:
        await sqs_client.send_message(
            QueueUrl=REQUEST_QUEUE_URL,
            MessageBody=message_json
        )
        print("request pushed")
        return image_name

async def monitor_sqs_s3():
    global pending_requests, last_request_time
    while True:
        if pending_requests:
            await scaling_controller()
            last_request_time = time.time()
        if time.time()-last_request_time>300:
            pending_requests = False
        await asyncio.sleep(1)

async def startup_event():
    asyncio.create_task(monitor_sqs_s3())

async def get_stored_response(request_id):
    while True:
        if request_id in response_store:
            return response_store[request_id]
        else:
            await asyncio.sleep(1)

async def get_data_From_msg(message_body):
    image_id = message_body['image_name']
    image_result = message_body['image_result']
    return image_id, image_result

# async def process_response():
#     try:
#         async with session.client('sqs') as sqs_client:
#             receive_response = await sqs_client.receive_message(
#                 QueueUrl=RESPONSE_QUEUE_URL,
#                 AttributeNames=['SentTimestamp'],
#                 MaxNumberOfMessages=1,
#                 MessageAttributeNames=['All'],
#                 VisibilityTimeout=5,
#                 WaitTimeSeconds=20
#             )

#             if 'Messages' in receive_response:
#                 message = receive_response['Messages'][0]
#                 message_body = json.loads(message['Body'])
#                 image_id, image_result = await get_data_From_msg(message_body)
#                 response_store[image_id] = image_result
#                 print(f"output is: {image_result}")
#                 receipt_handle = message['ReceiptHandle']
#                 async with session.client('sqs') as sqs_client:
#                     await sqs_client.delete_message(
#                         QueueUrl=RESPONSE_QUEUE_URL,
#                         ReceiptHandle=receipt_handle
#                     )
#             else:
#                 print("No messages received")
#     except Exception as e:
#         print(f"Error processing response: {e}")

async def process_response_retries(delay=2, max_retries=200):
    retries = 0

    while retries < max_retries:
        try:
            async with session.client('sqs') as sqs_client:
                receive_response = await sqs_client.receive_message(
                    QueueUrl=RESPONSE_QUEUE_URL,
                    AttributeNames=['SentTimestamp'],
                    MaxNumberOfMessages=1,
                    MessageAttributeNames=['All'],
                    VisibilityTimeout=5,
                    WaitTimeSeconds=20
                )

                if 'Messages' in receive_response:
                    message = receive_response['Messages'][0]
                    message_body = json.loads(message['Body'])
                    image_id, image_result = await get_data_From_msg(message_body)
                    response_store[image_id] = image_result
                    print(f"output is: {image_result}")
                    receipt_handle = message['ReceiptHandle']
                    async with session.client('sqs') as sqs_client:
                        await sqs_client.delete_message(
                            QueueUrl=RESPONSE_QUEUE_URL,
                            ReceiptHandle=receipt_handle
                        )
                    return
                else:
                    print("No messages received")
        except Exception as e:
            print(f"Error processing response: {e}")

        retries+=1

        print(f"Retrying in {delay} seconds...")
        await asyncio.sleep(delay)

    print("Max retries reached, giving up.")

@app.post("/", response_class=PlainTextResponse)
async def get_app_result(inputFile: UploadFile):

    global pending_requests
    pending_requests = True

    file_content = await inputFile.read()
    image_name = inputFile.filename.split('.')[0]

    request_id = await process_request(file_content, image_name)
    # await process_response()
    await process_response_retries()
    response = await get_stored_response(request_id)
    return response

app.add_event_handler("startup", startup_event)