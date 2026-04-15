"""
Provision AWS RDS (PostgreSQL) and MongoDB (via Docker on backend EC2).
- Creates RDS PostgreSQL t3.micro in the same SG as the EC2 instances
- Installs MongoDB via Docker on the backend EC2 instance
- Prints connection strings for use in the backend
"""
import boto3
import time
import paramiko

# Config
REGION = "us-east-1"
SG_ID = "sg-0c699beaafbc840de"
BACKEND_IP = "52.73.177.176"
KEY_PATH = "backend/labsuser.pem"
DB_USERNAME = "planapp"
DB_PASSWORD = "PlanLector2024!"
DB_NAME = "planLectorDB"

def get_subnet_ids(ec2_client):
    """Get the subnet IDs for the VPC used by the SG"""
    sg = ec2_client.describe_security_groups(GroupIds=[SG_ID])
    vpc_id = sg['SecurityGroups'][0]['VpcId']
    subnets = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    ids = [s['SubnetId'] for s in subnets['Subnets']]
    print(f"VPC: {vpc_id}, Subnets: {ids}")
    return vpc_id, ids

def open_postgres_port(ec2_client):
    """Open port 5432 in the security group"""
    print("Opening port 5432 for PostgreSQL...")
    try:
        ec2_client.authorize_security_group_ingress(
            GroupId=SG_ID,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 5432, 'ToPort': 5432, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 27017, 'ToPort': 27017, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            ]
        )
        print("Ports 5432 and 27017 opened.")
    except Exception as e:
        print(f"Port already open or skipped: {e}")

def create_rds_postgres(rds_client, subnet_ids, vpc_id):
    """Create an RDS PostgreSQL instance"""
    # Create a DB subnet group first
    try:
        print("Creating DB subnet group...")
        rds_client.create_db_subnet_group(
            DBSubnetGroupName='plan-lector-subnet-group',
            DBSubnetGroupDescription='Plan Lector DB subnet group',
            SubnetIds=subnet_ids[:2],  # Need at least 2 subnets in different AZs
        )
        print("Subnet group created.")
    except rds_client.exceptions.DBSubnetGroupAlreadyExistsFault:
        print("Subnet group already exists, reusing.")
    except Exception as e:
        print(f"Subnet group error: {e}")

    # Create RDS instance
    try:
        print("Creating RDS PostgreSQL instance (t3.micro)...")
        response = rds_client.create_db_instance(
            DBInstanceIdentifier='plan-lector-postgres',
            DBInstanceClass='db.t3.micro',
            Engine='postgres',
            EngineVersion='15',
            MasterUsername=DB_USERNAME,
            MasterUserPassword=DB_PASSWORD,
            DBName=DB_NAME,
            AllocatedStorage=20,
            StorageType='gp2',
            VpcSecurityGroupIds=[SG_ID],
            DBSubnetGroupName='plan-lector-subnet-group',
            PubliclyAccessible=True,
            BackupRetentionPeriod=0,
            MultiAZ=False,
            Tags=[{'Key': 'Name', 'Value': 'plan-lector-postgres'}]
        )
        db = response['DBInstance']
        print(f"RDS instance '{db['DBInstanceIdentifier']}' creation initiated.")
        return db['DBInstanceIdentifier']
    except rds_client.exceptions.DBInstanceAlreadyExistsFault:
        print("RDS instance already exists, fetching endpoint...")
        db = rds_client.describe_db_instances(DBInstanceIdentifier='plan-lector-postgres')['DBInstances'][0]
        return db['DBInstanceIdentifier']
    except Exception as e:
        print(f"RDS creation error: {e}")
        return None

def wait_for_rds(rds_client, db_id):
    """Wait for RDS to be available and return its endpoint"""
    print("Waiting for RDS instance to be available (this takes ~5 min)...")
    for i in range(40):
        db = rds_client.describe_db_instances(DBInstanceIdentifier=db_id)['DBInstances'][0]
        status = db['DBInstanceStatus']
        print(f"  [{i*15}s] Status: {status}")
        if status == 'available':
            host = db['Endpoint']['Address']
            port = db['Endpoint']['Port']
            print(f"RDS ready at: {host}:{port}")
            return host, port
        time.sleep(15)
    print("RDS not ready in time, check AWS console.")
    return None, None

def install_mongodb_on_ec2():
    """SSH into backend EC2 and run MongoDB via Docker"""
    print(f"\nConnecting to backend EC2 ({BACKEND_IP}) to install MongoDB via Docker...")
    key = paramiko.RSAKey.from_private_key_file(KEY_PATH)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(BACKEND_IP, username='ubuntu', pkey=key)

    commands = [
        # Ensure docker is installed
        "command -v docker || (curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sudo sh /tmp/get-docker.sh)",
        # Pull and run MongoDB
        "sudo docker stop mongodb || true",
        "sudo docker rm mongodb || true",
        f"sudo docker run -d --name mongodb --restart unless-stopped -p 27017:27017 "
        f"-e MONGO_INITDB_ROOT_USERNAME={DB_USERNAME} "
        f"-e MONGO_INITDB_ROOT_PASSWORD={DB_PASSWORD} "
        f"-e MONGO_INITDB_DATABASE={DB_NAME} "
        f"-v mongodb_data:/data/db mongo:6",
        "sudo docker ps | grep mongodb",
    ]

    for cmd in commands:
        print(f"  > {cmd[:80]}...")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(f"    OUT: {out}")
        if err and 'WARNING' not in err.upper():
            print(f"    ERR: {err}")
        time.sleep(2)

    client.close()
    print("MongoDB running on backend EC2 on port 27017.")
    return BACKEND_IP

def main():
    session = boto3.Session(region_name=REGION)
    ec2_client = session.client('ec2')
    rds_client = session.client('rds')

    # 1. Open required ports
    open_postgres_port(ec2_client)

    # 2. Get networking info
    vpc_id, subnet_ids = get_subnet_ids(ec2_client)

    # 3. Create RDS PostgreSQL
    db_id = create_rds_postgres(rds_client, subnet_ids, vpc_id)

    # 4. Install MongoDB on backend EC2 via Docker
    mongo_host = install_mongodb_on_ec2()

    # 5. Wait for RDS and get endpoint
    if db_id:
        pg_host, pg_port = wait_for_rds(rds_client, db_id)
    else:
        pg_host, pg_port = None, None

    # 6. Print connection strings
    print("\n" + "="*50)
    print("CONNECTION STRINGS FOR BACKEND")
    print("="*50)
    if pg_host:
        pg_url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{pg_host}:{pg_port}/{DB_NAME}"
        print(f"PostgreSQL: {pg_url}")
    mongo_url = f"mongodb://{DB_USERNAME}:{DB_PASSWORD}@{mongo_host}:27017/{DB_NAME}?authSource=admin"
    print(f"MongoDB:    {mongo_url}")
    print("="*50)
    print("\nAdd these as GitHub Secrets:")
    print(f"  DATABASE_URL = {pg_url if pg_host else 'pending-rds-ready'}")
    print(f"  MONGODB_URL  = {mongo_url}")

if __name__ == "__main__":
    main()
