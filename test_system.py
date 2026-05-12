import requests
import json

def run_test():
    url = "http://127.0.0.1:8000/verify"
    payload = {
        "node_id": "00000000-0000-0000-0000-000000000001",
        "claim_text": "India just signed a $100 billion trade deal with EFTA."
    }
    
    print(f"Sending payload to {url}:")
    print(json.dumps(payload, indent=2))
    print("-" * 40)
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        print("Response received:")
        print(json.dumps(response.json(), indent=4))
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    run_test()
