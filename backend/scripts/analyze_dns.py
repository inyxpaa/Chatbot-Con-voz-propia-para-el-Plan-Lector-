import boto3
session = boto3.Session(region_name='us-east-1')
ec2 = session.client('ec2')
instances = ec2.describe_instances()['Reservations']
for r in instances:
    for i in r['Instances']:
        if i['State']['Name'] == 'running':
            print(f"Public IP: {i.get('PublicIpAddress')}")
            print(f"Public DNS: {i.get('PublicDnsName')}")
            print('-'*20)
