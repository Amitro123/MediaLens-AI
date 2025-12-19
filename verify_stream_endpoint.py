import requests

try:
    url = "http://localhost:8000/api/v1/stream/mtg_1"
    print(f"Checking {url}...")
    
    # Test 1: Head request (skipped due to 405)
    # r = requests.head(url)
    # print(f"HEAD Status: {r.status_code}")
    
    # Test 2: Range request
    headers = {"Range": "bytes=0-100"}
    r = requests.get(url, headers=headers)
    print(f"Range GET Status: {r.status_code}")
    if r.status_code == 206:
        print("SUCCESS: 206 Partial Content received!")
        print(f"Content-Range: {r.headers.get('Content-Range')}")
    else:
        print(f"FAILURE: Expected 206, got {r.status_code}")

except Exception as e:
    print(f"Error: {e}")
