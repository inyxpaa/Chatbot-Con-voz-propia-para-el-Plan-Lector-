import boto3
import time

def main():
    try:
        session = boto3.Session(region_name='us-east-1')
        ec2 = session.client('ec2')
        ec2_resource = session.resource('ec2')
        
        # AMI ami-05e86b3611c60b0b4 is ubuntu 22.04 from earlier
        # Try to open ports first
        sg_id = 'sg-0c699beaafbc840de'
        print("Authorizing SG ingress...")
        try:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'UserIdGroupPairs': [{'GroupId': sg_id}]}
                ]
            )
            print("SG ingress rules updated.")
        except Exception as e:
            print(f"Modifying SG failed (probably due to lab restrictions, or rules already exist): {e}")

        # Launch Frontend instance
        print("Launching Frontend...")
        frontend = ec2_resource.create_instances(
            ImageId='ami-05e86b3611c60b0b4',
            MinCount=1, MaxCount=1,
            InstanceType='t2.micro',
            KeyName='vockey',
            SecurityGroupIds=[sg_id],
            TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'Frontend-App'}]}]
        )[0]
        
        # Launch Backend instance
        print("Launching Backend...")
        backend = ec2_resource.create_instances(
            ImageId='ami-05e86b3611c60b0b4',
            MinCount=1, MaxCount=1,
            InstanceType='t2.micro',
            KeyName='vockey',
            SecurityGroupIds=[sg_id],
            TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'Backend-App'}]}]
        )[0]

        print("Waiting for instances to be running...")
        frontend.wait_until_running()
        backend.wait_until_running()
        
        frontend.reload()
        backend.reload()
        
        print("\n------- SUCCESS -------")
        print(f"FRONTEND_IP: {frontend.public_ip_address}")
        print(f"BACKEND_IP: {backend.public_ip_address}")

    except Exception as e:
        print(f"Error launching instances: {e}")

if __name__ == "__main__":
    main()
