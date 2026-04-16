import boto3
import os

def get_instance_details(instance_id):
    # Use credentials from the environment if available, or hardcode if needed (but env is better)
    # The user provided them in the prompt, so I'll assume they are configured or I can pass them.
    session = boto3.Session()
    ec2 = session.client('ec2', region_name='us-east-1')
    
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instance = response['Reservations'][0]['Instances'][0]
    
    print(f"Instance ID: {instance['InstanceId']}")
    print(f"Type: {instance['InstanceType']}")
    print(f"Public IP: {instance.get('PublicIpAddress', 'N/A')}")
    
    # Check for Elastic IP
    eip_response = ec2.describe_addresses(Filters=[{'Name': 'instance-id', 'Values': [instance_id]}])
    addresses = eip_response.get('Addresses', [])
    if addresses:
        print(f"Elastic IP Found: {addresses[0]['PublicIp']}")
    else:
        print("ALERT: No Elastic IP found. The IP will likely change after restart!")

    # Check Volume ID
    for mapping in instance['BlockDeviceMappings']:
        if mapping['DeviceName'] in ['/dev/sda1', '/dev/xvda', '/dev/root']:
            print(f"Volume ID: {mapping['Ebs']['VolumeId']}")

if __name__ == "__main__":
    get_instance_details('i-032db7a9cfabf7bf5')
