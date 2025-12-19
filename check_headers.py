import requests

try:
    url = "http://localhost:8000/uploads/mtg_2/video.mp4"
    print(f"Checking {url}...")
    r = requests.head(url)
    print(f"Status: {r.status_code}")
    print("Headers:")
    for k, v in r.headers.items():
        print(f"  {k}: {v}")
        
    if "accept-ranges" in r.headers:
        print("\nSUCCESS: Accept-Ranges header found!")
    else:
        print("\nFAILURE: Accept-Ranges header MISSING!")
except Exception as e:
    print(f"Error: {e}")
