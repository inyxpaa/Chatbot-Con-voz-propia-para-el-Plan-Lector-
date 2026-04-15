import paramiko
import time

BACKEND_IP = "34.224.57.208"
KEY_PATH = "backend/labsuser.pem"
DB_USERNAME = "planapp"
DB_PASSWORD = "PlanLector2024!"
DB_NAME = "planLectorDB"

key = paramiko.RSAKey.from_private_key_file(KEY_PATH)
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(BACKEND_IP, username='ubuntu', pkey=key)

def run(cmd, wait=3):
    print(f"> {cmd[:100]}")
    stdin, stdout, stderr = client.exec_command(cmd)
    time.sleep(wait)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(f"  OUT: {out}")
    if err: print(f"  ERR: {err}")
    return out

# Check disk space
run("df -h /")

# Prune docker to free space (removes unused images/containers)
run("sudo docker system prune -af --volumes", wait=10)

# Check again
run("df -h /")

# Pull and run MongoDB (lightweight -- no auth for internal use)
run("sudo docker pull mongo:6", wait=60)
run("sudo docker stop mongodb || true")
run("sudo docker rm mongodb || true")
run(
    f"sudo docker run -d --name mongodb --restart unless-stopped -p 27017:27017 "
    f"-e MONGO_INITDB_ROOT_USERNAME={DB_USERNAME} "
    f"-e MONGO_INITDB_ROOT_PASSWORD={DB_PASSWORD} "
    f"-e MONGO_INITDB_DATABASE={DB_NAME} "
    f"-v mongodb_data:/data/db mongo:6",
    wait=5
)

run("sudo docker ps")
print("\nDone!")
client.close()
