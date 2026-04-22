import boto3
import time
import os

instance_id = 'i-032db7a9cfabf7bf5'
volume_id = 'vol-0accd9aff1ddf5aeb'
region = 'us-east-1'

session = boto3.Session()
ec2 = session.client('ec2', region_name=region)

def upgrade_infrastructure():
    # 1. Expand EBS Volume to 20GB
    print(f"Expanding volume {volume_id} to 20GB...")
    try:
        ec2.modify_volume(VolumeId=volume_id, Size=20)
        print("Volume modification requested.")
    except Exception as e:
        print(f"Error modifying volume: {e}")

    # 2. Stop the Instance
    print(f"Stopping instance {instance_id}...")
    ec2.stop_instances(InstanceIds=[instance_id])
    
    waiter = ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=[instance_id])
    print("Instance stopped.")

    # 3. Change Instance Type
    print(f"Changing instance type to t3.medium...")
    ec2.modify_instance_attribute(InstanceId=instance_id, InstanceType={'Value': 't3.medium'})
    print("Instance type changed.")

    # 4. Start the Instance
    print(f"Starting instance {instance_id}...")
    ec2.start_instances(InstanceIds=[instance_id])
    
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print("Instance started and running.")

if __name__ == "__main__":
    upgrade_infrastructure()
