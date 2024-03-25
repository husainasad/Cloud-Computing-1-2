import boto3, json

with open('config.json') as f:
    config = json.load(f)

SQS_Names = [config["REQUEST_QUEUE"], config["RESPONSE_QUEUE"]]
AWS_REGION = config['AWS_REGION']

session = boto3.Session()
sqs_client = session.client('sqs', region_name=AWS_REGION)

for name in SQS_Names:
    response = sqs_client.create_queue(QueueName = name)
    print(response)