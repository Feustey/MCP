import requests

# Token simplifié pour le test
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXpsbmciLCJyb2xlIjoiYWRtaW4ifQ.qwerty123"

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get("http://localhost:8002/health", headers=headers)
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}") 