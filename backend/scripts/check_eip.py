import boto3
import os

def check_aws():
    try:
        session = boto3.Session(region_name='us-east-1')
        ec2 = session.client('ec2')
        
        print("--- EC2 Instances ---")
        instances = ec2.describe_instances()
        for res in instances['Reservations']:
            for ins in res['Instances']:
                name = "Unnamed"
                if 'Tags' in ins:
                    for tag in ins['Tags']:
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                print(f"ID: {ins['InstanceId']}, Name: {name}, State: {ins['State']['Name']}, Public IP: {ins.get('PublicIpAddress', 'None')}")
        
        print("\n--- EIP Allocation Check ---")
        try:
            # Note: This list_addresses call might fail if not allowed, but it's a good test
            eips = ec2.describe_addresses()
            print(f"Current EIPs: {len(eips['Addresses'])}")
            for addr in eips['Addresses']:
                print(f"EIP: {addr['PublicIp']}, AllocationId: {addr['AllocationId']}")
        except Exception as e:
            print(f"Error checking EIPs: {e}")

    except Exception as e:
        print(f"AWS Connection Error: {e}")

if __name__ == "__main__":
    check_aws()
