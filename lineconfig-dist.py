import base64
import hashlib
import hmac

CHANNELSECRET='書いてね'
CHANNELACCESSTOKEN='書いてね'
BROADCASTAPIURL='https://api.line.me/v2/bot/message/broadcast'
PUSHAPIURL='https://api.line.me/v2/bot/message/push'
REPLYAPIURL='https://api.line.me/v2/bot/message/reply'
DATAAPIURL='https://api-data.line.me/v2/bot/message' # /{messageId}/content'

def validate_signature(body,signature):
    hash = hmac.new(CHANNELSECRET.encode('utf-8'),
        body.encode('utf-8'), hashlib.sha256).digest()
    return  base64.b64encode(hash) == signature.encode('utf-8')
