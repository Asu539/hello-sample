import requests
import json
import lineconfig

headers={
   'Content-Type': 'application/json',
   'Authorization': "Bearer "+lineconfig.CHANNELACCESSTOKEN
}

payload={
    'messages':[
        {
        'type':'text',
        'text':'Hello, World1'
        },
        {
        'type':'text',
        'text':'日本語も通る?'
        }
    ]
}
response = requests.post(lineconfig.BROADCASTAPIURL, data=json.dumps(payload),headers=headers)
print(response.status_code) 
print(response.text) 