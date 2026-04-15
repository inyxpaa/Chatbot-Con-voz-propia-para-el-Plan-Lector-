import paramiko

def main():
    ip = '34.224.57.208'
    key_path = 'backend/labsuser.pem'
    
    key = paramiko.RSAKey.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname=ip, username='ubuntu', pkey=key)
        stdin, stdout, stderr = client.exec_command('sudo docker logs backend-app')
        print(stdout.read().decode('utf-8'))
        err = stderr.read().decode('utf-8')
        if err:
            print("ERROR LOGS:")
            print(err)
            
        stdin, stdout, stderr = client.exec_command('sudo docker ps -a')
        print("DOCKER PS:")
        print(stdout.read().decode('utf-8'))
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    main()
