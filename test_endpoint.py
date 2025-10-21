import requests

url = "http://127.0.0.1:8000/api/shop/products/"
params = {"in_stock": "true", "page_size": "8"}

print("Testing endpoint:", url)
print("Params:", params)
print("=" * 60)

try:
    response = requests.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
