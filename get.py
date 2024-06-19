import requests

response = requests.get('https://www.ryukoku.ac.jp')
print(response.status_code) 
print(response.text) 