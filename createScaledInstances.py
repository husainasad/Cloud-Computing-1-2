import boto3, json

with open('config.json') as f:
    config = json.load(f)

AMI_ID = config['AMI_ID']
AWS_REGION = config['AWS_REGION']
SECURITY_GROUP = config['SECURITY_GROUP']
instance_name = config["APP_INSTANCE_NAME"]
instance_num = config["MAX_SERVERS"]

session = boto3.Session()
ec2_client = session.client('ec2', region_name=AWS_REGION)

for i in range(1, instance_num + 1):
    name = instance_name + str(i)
    instance = ec2_client.run_instances(
        ImageId=AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        SecurityGroupIds=SECURITY_GROUP,
        IamInstanceProfile={'Name': 'ec2-full-access-role'},
        TagSpecifications=[{'ResourceType':'instance',
                            'Tags': [{
                                'Key': 'Name',
                                'Value': name }]}]
    )

    print(instance['Instances'][0]['InstanceId'])