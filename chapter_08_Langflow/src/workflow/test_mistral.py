import requests

API_KEY = "J472HmqvfMt8ByfaiavSv3VMD1B3Yt3f"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

try:
    response = requests.get(
        "https://api.mistral.ai/v1/models",
        headers=headers,
        timeout=30
    )

    print("Status:", response.status_code)
    print(response.text)

except Exception as e:
    print(e)