import os
import requests
from dotenv import load_dotenv

# 1. Load the environment
load_dotenv()
token = os.getenv("HF_API_TOKEN")

print("--- HUGGING FACE API DIAGNOSTIC ---")
if not token:
    print("❌ ERROR: HF_API_TOKEN is missing from .env!")
    exit()
else:
    print(f"✅ Token loaded successfully (Starts with: {token[:6]}...)")

# 2. Configure the target
URL = "https://api-inference.huggingface.co/models/MoritzLaurer/DeBERTa-v3-large-mnli"
headers = {"Authorization": f"Bearer {token}"}
payload = {"inputs": "Premise: Kerala has high literacy. Hypothesis: Kerala has high literacy."}

# 3. Fire the payload
print("\nFiring request to DeBERTa... (Waiting for response)")
response = requests.post(URL, headers=headers, json=payload, timeout=30)

# 4. The Autopsy
print(f"\nHTTP Status Code: {response.status_code}")
print("Raw Text Response from Hugging Face:")
print("-" * 40)
print(response.text)
print("-" * 40)

# 5. JSON Parsing Test
try:
    data = response.json()
    print("✅ JSON Parsed Successfully!")
    print(data)
except Exception as e:
    print(f"❌ JSON Parse Crashed: {e}")