from Resources.model.face_recognition import face_match
import boto3, base64, json, asyncio

AWS_REGION = 'us-east-1'
REQUEST_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/223420481310/1225380117-req-queue'
RESPONSE_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/223420481310/1225380117-resp-queue'
IN_BUCKET = '1225380117-in-bucket'
OUT_BUCKET = '1225380117-out-bucket'

sts_client = boto3.client('sts')

session = boto3.Session()

sqs_client = session.client('sqs', region_name=AWS_REGION)

s3_client = session.client('s3')

data_pt_path = './Resources/model/data.pt'

async def process_img(image_data):
    try:
        # image_data = base64.b64decode(encoded_img)
        with open('temp.jpg', 'wb') as f:
            f.write(image_data)
        result = face_match('temp.jpg', data_pt_path)[0]
        return f'{result}'
    except Exception as e:
        return f"Error: {str(e)}"
    

async def process_msg():
    while True:
        receive_response = sqs_client.receive_message(
            QueueUrl=REQUEST_QUEUE_URL,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )

        if 'Messages' in receive_response:
            message = receive_response['Messages'][0]
            
            message_body = json.loads(message['Body'])

            image_name = message_body['image_name']
            # print('image name is: ' + image_name)

            image_encoded = message_body['image_encoded']
            image_data = base64.b64decode(image_encoded)

            # print('Received image data from SQS')

            model_result = await process_img(image_data)

            # Add request and response in S3 buckets
            s3_client.put_object(Body=image_data, Bucket=IN_BUCKET, Key=image_name + '.jpg')
            s3_client.put_object(Body=model_result, Bucket=OUT_BUCKET, Key=image_name)

            # Delete received message from queue
            receipt_handle = message['ReceiptHandle']
            sqs_client.delete_message(
                QueueUrl=REQUEST_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            # print('Deleted message')
            
            output_msg = f'{image_name}:{model_result}'
            # print(output_msg)

            sqs_client.send_message(
                QueueUrl=RESPONSE_QUEUE_URL,
                MessageBody=(
                    output_msg
                )
            )

            # print(f"Message sent to Response SQS with MessageId: {send_response['MessageId']}")


if __name__ == "__main__":
    # process_msg()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_msg())