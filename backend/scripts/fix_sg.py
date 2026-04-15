import boto3

def fix_security_group():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    sg_id = 'sg-0c699beaafbc840de'
    
    print(f"Cleaning up Security Group: {sg_id}")
    
    # 1. Revoke public rules for 8000, 5432, 27017
    try:
        ec2.revoke_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 27017, 'ToPort': 27017, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            ]
        )
        print("Revoked public access for 8000, 5432, 27017.")
    except Exception as e:
        print(f"Revoke failed (maybe they don't exist?): {e}")

    # 2. Re-authorize as internal only (self-referencing)
    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp', 
                    'FromPort': 8000, 
                    'ToPort': 8000, 
                    'UserIdGroupPairs': [{'GroupId': sg_id}]
                },
                {
                    'IpProtocol': 'tcp', 
                    'FromPort': 5432, 
                    'ToPort': 5432, 
                    'UserIdGroupPairs': [{'GroupId': sg_id}]
                },
                {
                    'IpProtocol': 'tcp', 
                    'FromPort': 27017, 
                    'ToPort': 27017, 
                    'UserIdGroupPairs': [{'GroupId': sg_id}]
                }
            ]
        )
        print("Authorized internal access for 8000, 5432, 27017.")
    except Exception as e:
        print(f"Authorize failed (maybe already exist?): {e}")

if __name__ == "__main__":
    fix_security_group()
