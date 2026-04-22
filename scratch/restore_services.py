import subprocess
import os

key_path = r"C:\Users\Vespertino\aws_key.pem"
frontend_ip = "44.218.99.64"
backend_ip = "34.195.154.105"

def run_ssh(ip, user, commands):
    print(f"--- Executing on {user}@{ip} ---")
    full_cmd = " && ".join(commands)
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-i", key_path,
        f"{user}@{ip}",
        full_cmd
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Error output: {result.stderr}")
        return result.returncode
    except Exception as e:
        print(f"Execution failed: {e}")
        return -1

# Frontend commands
print("Restoring Frontend...")
run_ssh(frontend_ip, "ubuntu", [
    "sudo docker update --restart always frontend-app",
    "sudo docker start frontend-app",
    "sudo docker ps"
])

# Backend commands
print("\nRestoring Backend...")
run_ssh(backend_ip, "ubuntu", [
    "sudo docker update --restart always backend-app",
    "sudo docker start backend-app",
    "sudo docker ps"
])
