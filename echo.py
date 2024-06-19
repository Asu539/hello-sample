from flask import Flask, request
import requests
import json
import lineconfig

app = Flask(__name__)

@app.route('/callback', methods=['POST'])
def response():
    posted_data=request.data
    posted_object=json.loads(posted_data.decode('utf8'))
    response_to_line=''
    print("=request from LINE Messaging API")
    print(request.data) ## or request.get_data()
    print("---")
    print(posted_object)

    # 本当に LINE Messaging API からの POST か?
    # 本当はイベントタイプがmessageであることもヘッダーから確認する必要 https://developers.line.biz/ja/docs/messaging-api/receiving-messages/
    if not lineconfig.validate_signature(request.get_data(as_text=True),request.headers['x-line-signature']):
        print("signature mismatch")
        # do nothing
        return response_to_line
    
    headers={
       'Content-Type': 'application/json',
       'Authorization': "Bearer "+lineconfig.CHANNELACCESSTOKEN
    }
 
    payload={
        'replyToken':posted_object['events'][0]['replyToken'],
        'messages':[{
            'type':'text',
            'text':posted_object['events'][0]['message']['text']
            }
        ]
    }
    print("=request to LINE Messaging API")
    print(payload)

    response = requests.post(lineconfig.REPLYAPIURL, data=json.dumps(payload),headers=headers)
    print("=response from LINE Messaging API")
    print(response)

    response_to_line=''
    return response_to_line
    #    print(response.status_code) 
    #    print(response.text) 

# お約束
if __name__ == '__main__':
    print("afo")
    allowed_host='0.0.0.0'
    server_port=3000
    app.debug=True
    app.run(host=allowed_host,port=server_port)