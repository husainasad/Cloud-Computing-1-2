import boto3, json

with open('config.json') as f:
    config = json.load(f)

S3_Names = [config["IN_BUCKET"], config["OUT_BUCKET"]]

session = boto3.Session()
s3_client = session.client('s3')

for name in S3_Names:
    response = s3_client.create_bucket(Bucket = name)
    print(response)