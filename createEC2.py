import boto3, json

with open('config.json') as f:
    config = json.load(f)

AWS_REGION = config['AWS_REGION']
AMI_ID = config['AMI_ID']
SECURITY_GROUP = config['SECURITY_GROUP']
WEB_SERVER_NAME = config['WEB_SERVER_NAME']
APP_SERVER_NAME = config['APP_SERVER_NAME']

instance_data = {
    WEB_SERVER_NAME: open("web-instance-script.txt", "r").read(),
    APP_SERVER_NAME: open("app-instance-script.txt", "r").read()
}

session = boto3.Session()
ec2_client = session.client('ec2', region_name=AWS_REGION)

for name, user_data in instance_data.items():
    instance = ec2_client.run_instances(
        ImageId=AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        SecurityGroupIds=SECURITY_GROUP,
        IamInstanceProfile={'Name': 'ec2-full-access-role'},
        UserData=user_data,
        TagSpecifications=[{'ResourceType':'instance',
                            'Tags': [{
                                'Key': 'Name',
                                'Value': name }]}]
    )

    print(instance['Instances'][0]['InstanceId'])