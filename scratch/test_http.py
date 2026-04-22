import requests

ips = ["44.218.99.64", "34.195.154.105"]

for ip in ips:
    print(f"Testing http://{ip}...")
    try:
        r = requests.get(f"http://{ip}", timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Headers: {r.headers}")
        print(f"Content snippet: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)
