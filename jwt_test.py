import base64
import jwt
from MainShortcuts2 import ms
def get_access_token()->str:
  data=ms.json.read("settings.json")
  return data["userSettings"]["stdruntime"]["oauthAccessToken"]
def get_pub_key()->str:
  return "-----BEGIN PUBLIC KEY-----\n%s\n-----END PUBLIC KEY-----"%base64.b64encode(ms.file.load("ecdsa_id.pub")).decode()
def decode_access_token()->dict:
  return jwt.decode(get_access_token(),get_pub_key(),algorithms=["ES256"])