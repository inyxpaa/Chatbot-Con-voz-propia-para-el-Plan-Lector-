import subprocess
import os

key_path = r"C:\Users\Vespertino\aws_key.pem"
frontend_ip = "44.218.99.64"
backend_ip = "34.195.154.105"

def run_ssh(ip, user, command):
    print(f"Trying {user}@{ip}...")
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
        "-i", key_path,
        f"{user}@{ip}",
        command
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), -1

for ip in [frontend_ip, backend_ip]:
    print(f"\n--- Checking {ip} ---")
    for user in ["ubuntu", "ec2-user"]:
        out, err, code = run_ssh(ip, user, "docker ps -a")
        if code == 0:
            print(f"Success as {user}!")
            print(out)
            break
        else:
            print(f"Failed as {user}: {err}")
