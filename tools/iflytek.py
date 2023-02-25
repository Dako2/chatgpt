# -*- coding:utf-8 -*-
#https://global.xfyun.cn/doc/rtasr/rtasr/API.html

import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import subprocess
subprocess.call("chcp 936", shell=True)

STATUS_FIRST_FRAME = 0  # 
STATUS_CONTINUE_FRAME = 1  
STATUS_LAST_FRAME = 2  

class Ws_Param(object):
    # Initialization
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        self.CommonArgs = {"app_id": self.APPID}
       
        self.BusinessArgs = {"domain": "ist_open", "language": "zh_cn", "accent": "mandarin"}#en_us

    # Generate url
    def create_url(self):
        url = 'wss://ist-api-sg.xf-yun.com/v2/ist'
        # Generate timestamp in RCF1123 format.
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

     
        signature_origin = "host: " + "ist-api-sg.xf-yun.com" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/ist " + "HTTP/1.1"
        # Encrypt with hmac-sha256 
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
     
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ist-api-sg.xf-yun.com"
        }
        # Concat authentication parameters to generate url 
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
  
        # print('websocket url :', url)
        return url


# Process when you receive the websocket message 
def on_message(ws, message):
    try:
        code = json.loads(message)["code"]
        sid = json.loads(message)["sid"]
        if code != 0:
            errMsg = json.loads(message)["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))

        else:
            data = json.loads(message)["data"]["result"]["ws"]
            #print(json.loads(message))
            result = ""
            for i in data:
                for w in i["cw"]:
                    result += w["w"]
            #print("sid:%s call success!,data is:%s" % (sid, json.dumps(data, ensure_ascii=False)))
            print(result)

    except Exception as e:
        print("receive msg,but parse exception:", e)



# Process when you receive the websocket error
def on_error(ws, error):
    print("### error:", error)


# Process when you receive the disabled websocket 
def on_close(ws):
    print("### closed ###")


#Process when you receive websocket connection has been established 
def on_open(ws):
    def run(*args):
        frameSize = 1280  
        intervel = 0.04  
        status = STATUS_FIRST_FRAME  

        with open(wsParam.AudioFile, "rb") as fp:
            while True:
                buf = fp.read(frameSize)
                if not buf:
                    status = STATUS_LAST_FRAME
                # The first frame processing
                # When you send the first frame audio, please carry the bussiness parameter.
                # You may carry the appid in the first frame.
                if status == STATUS_FIRST_FRAME:

                    d = {"common": wsParam.CommonArgs,
                         "business": wsParam.BusinessArgs,
                         "data": {"status": 0, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    d = json.dumps(d)
                    ws.send(d)
                    status = STATUS_CONTINUE_FRAME
                # Middle frame processing
                elif status == STATUS_CONTINUE_FRAME:
                    d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                # Last frame processing
                elif status == STATUS_LAST_FRAME:
                    d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                    time.sleep(1)
                    break
                # Simulate the audio sample interval
                time.sleep(intervel)
        ws.close()

    thread.start_new_thread(run, ())


if __name__ == "__main__":
    # While testing, fill in the relevant information correctly here to operate. 
    time1 = datetime.now()
    wsParam = Ws_Param(APPID='g9ff5fa1', APISecret='038a91d06a874a13491445b075a15781',
                       APIKey='bd795dcd0ffebf0f5dfcf68bfc79f14d',
                       AudioFile=r'C:/Users/tqidt/git/recording.pcm')
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    time2 = datetime.now()
    print(time2-time1)
    
