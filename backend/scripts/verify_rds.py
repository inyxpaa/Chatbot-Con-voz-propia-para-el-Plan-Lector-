import boto3

def verify_rds():
    try:
        session = boto3.Session(region_name='us-east-1')
        rds = session.client('rds')
        dbs = rds.describe_db_instances()
        
        print("--- RDS Status ---")
        if not dbs['DBInstances']:
            print("No RDS instances found.")
            return
            
        for db in dbs['DBInstances']:
            ident = db['DBInstanceIdentifier']
            status = db['DBInstanceStatus']
            host = db.get('Endpoint', {}).get('Address', 'N/A')
            print(f"ID: {ident}, Status: {status}, Host: {host}")
            
    except Exception as e:
        print(f"Error checking RDS: {e}")

if __name__ == "__main__":
    verify_rds()
