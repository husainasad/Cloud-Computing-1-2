from fastapi import FastAPI, UploadFile
from fastapi.responses import PlainTextResponse
import boto3, base64, json, asyncio

app = FastAPI()

with open('config.json') as f:
    config = json.load(f)

AWS_REGION = config['AWS_REGION']
REQUEST_QUEUE_URL = config['REQUEST_QUEUE_URL']
RESPONSE_QUEUE_URL = config['RESPONSE_QUEUE_URL']
IN_BUCKET = config['IN_BUCKET']
APP_INSTANCE_NAME = config['APP_INSTANCE_NAME']
MAX_SERVERS = config['MAX_SERVERS']

sts_client = boto3.client('sts')
session = boto3.Session()

sqs_client = session.client('sqs', region_name=AWS_REGION)
ec2_client = session.client('ec2', region_name=AWS_REGION)

async def get_instances_with_tag(instance_name=APP_INSTANCE_NAME):
    response = ec2_client.describe_instances(
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
        await scale_up_servers(num=servers_required-current_servers)
    elif servers_required < current_servers:
        await scale_down_servers(num=current_servers-servers_required)

async def scale_up_servers(instance_name=APP_INSTANCE_NAME, num=1):
    instances = await get_instances_with_tag(instance_name)
    stopped_instances = [instance for instance in instances if instance['State']['Name'] in ['stopped', 'stopping']]
    if stopped_instances:
        instances_to_start = stopped_instances[:num]
        instance_ids = [instance['InstanceId'] for instance in instances_to_start]
        ec2_client.start_instances(InstanceIds=instance_ids)
    else:
        print("Cannot start any more instances. Number of running instances is equal to the max number.")
        return

async def scale_down_servers(instance_name=APP_INSTANCE_NAME, num=1):
    instances = await get_instances_with_tag(instance_name)
    running_instances = [instance for instance in instances if instance['State']['Name'] == 'running']
    if len(running_instances) < num:
        print("Cannot stop instances. Number of running instances is less than or equal to the required number.")
        return
    instances_to_stop = running_instances[:num]
    instance_ids = [instance['InstanceId'] for instance in instances_to_stop]
    ec2_client.stop_instances(InstanceIds=instance_ids)

async def get_sqs_length():
    response = sqs_client.get_queue_attributes(
        QueueUrl=REQUEST_QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    print(int(response['Attributes']['ApproximateNumberOfMessages']))
    return int(response['Attributes']['ApproximateNumberOfMessages'])

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

async def monitor_sqs_s3():
    while True:
        await scaling_controller()
        await asyncio.sleep(1)

async def startup_event():
    asyncio.ensure_future(monitor_sqs_s3())

async def process_response():
    receive_response = sqs_client.receive_message(
        QueueUrl=RESPONSE_QUEUE_URL,
        AttributeNames=['SentTimestamp'],
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All'],
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

    response = await response_task
    return response

app.add_event_handler("startup", startup_event)