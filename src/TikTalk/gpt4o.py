import os
import re
import requests
import json
import base64
import configparser

_config = configparser.ConfigParser()
# need parent folder!
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.ini')
print(config_path)
_config.read(config_path, encoding='utf-8')

# open ai
OPENAI_TOKEN = os.getenv('OPENAI_TOKEN',_config['GenAI'].get('OPENAI_TOKEN'))
OPENAI_TOKEN_URL = os.getenv('OPENAI_TOKEN_URL',_config['GenAI'].get('OPENAI_TOKEN_URL'))
OPENAI_HEALTH_URL = os.getenv('OPENAI_HEALTH_URL',_config['GenAI'].get('OPENAI_HEALTH_URL'))
OPENAI_MM_URL = os.getenv('OPENAI_MM_URL',_config['GenAI'].get('OPENAI_MM_URL'))
OPENAI_CHATGPT_URL = os.getenv('OPENAI_CHATGPT_URL',_config['GenAI'].get('OPENAI_CHATGPT_URL'))
OPENAI_USER_NAME = os.getenv('OPENAI_USER_NAME',_config['GenAI'].get('OPENAI_USER_NAME'))
OPENAI_PASSWORD = os.getenv('OPENAI_PASSWORD',_config['GenAI'].get('OPENAI_PASSWORD'))
OPENAI_APPLICATION_ID = os.getenv('OPENAI_APPLICATION_ID',_config['GenAI'].get('OPENAI_APPLICATION_ID'))
OPENAI_APPLICATION_NAME = os.getenv('OPENAI_APPLICATION_NAME',_config['GenAI'].get('OPENAI_APPLICATION_NAME'))
HEAD_TOKEN_KEY = os.getenv('HEAD_TOKEN_KEY',_config['GenAI'].get('HEAD_TOKEN_KEY'))



# 实现ask函数
def ask(msgs):
    # 读取当前选择的endpoint
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    
    current_endpoint = config.get('Endpoints', 'current')
    endpoint_section = f'Endpoint_{current_endpoint}'
    
    # 使用选择的endpoint的配置
    global OPENAI_TOKEN, OPENAI_MM_URL
    OPENAI_TOKEN = config.get(endpoint_section, 'token')
    OPENAI_MM_URL = config.get(endpoint_section, 'url')
    
    _token = "Bearer " + OPENAI_TOKEN
    resp = ask_with_msgs(_token, msgs)
    return resp
        

def get_token():
  url = OPENAI_TOKEN_URL
  payload = json.dumps({
    "input_token_state": {
      "token_type": "CREDENTIAL",
      "username": OPENAI_USER_NAME,
      "password": OPENAI_PASSWORD
    },
    "output_token_state": {
      "token_type": "JWT"
    }
  })
  headers = {
    'Content-Type': 'application/json'
  }

  response = requests.request("POST", url, headers=headers, data=payload, verify=False)

  token_json=response.json()

  token = token_json["issued_token"]

  print(token)
  print("~"*100)
  return token


def check_health():
    url = OPENAI_HEALTH_URL
    payload={}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload, verify=False)
    status=response.json()["status"]
    print(status)
    return status
# token = get_token()



def encode_image(image_path):
    # image_path = "C:/Data/image_4e443d9307.png"
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def ask_on_images(token, img_pths=[], prompt="" ):
    imgs_b64=[]
    for img_pth in img_pths:
        try:
            img_b64 = encode_image(img_pth)
            imgs_b64.append(img_b64)
        except:
            pass
            print("image not parsable")

    user_content=[{"type": "text", "text": prompt}]
    for base64_image in imgs_b64:
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})

    payload = json.dumps({
    "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": user_content}
    ],
    "temperature": 0.7,
    "top_p": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "max_tokens": 800,
    "stop": None,
    # "response_format": { "type":"json_object" },
    "stream": False
    })
    headers = {
    HEAD_TOKEN_KEY: token,
    'GAI-Platform-Application-ID': OPENAI_APPLICATION_ID,
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", OPENAI_MM_URL, headers=headers, data=payload, verify=False, timeout=180)
    print("-"*50)
    print(response.text)
    print("="*50)
    res_json=response.json()
    resp=res_json["choices"][0]["message"]["content"]
    return resp


def ask_with_msgs(token, msgs):
    # 从配置文件读取当前模型设置
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    current_model = config.get('GenAI', 'model', fallback='o1-all')
    
    payload = json.dumps({
        "model": current_model,  # 使用配置中的模型设置
        "messages": msgs,
        "stop": None,
        "stream": False
    })
    headers = {
    HEAD_TOKEN_KEY: token,
    'GAI-Platform-Application-ID': OPENAI_APPLICATION_ID,
    'Content-Type': 'application/json'
    }
    print("----> OPENAI_MM_URL: ", OPENAI_MM_URL)
    print("----> payload: ", payload)
    response = requests.request("POST", OPENAI_MM_URL, headers=headers, data=payload, verify=False, timeout=180)
    print("-"*50)
    print(response.text)
    print("="*50)
    res_json=response.json()
    resp=res_json["choices"][0]["message"]["content"]
    return resp







def to_json(raw_output):
    try:
        json_output = ""
        try:
            json_output = json.loads(raw_output)
        except Exception:
            json_output = robust_string_to_json(raw_output)

        if isinstance(json_output, dict):
            return json_output
        else:
            raise ValueError("Invalid JSON format.")
    except Exception as e:
        error_message = f"Error processing output: {repr(e)} "
        return raw_output

def robust_string_to_json(s: str) -> dict:
    # 鍏堝皾璇曠洿鎺ヨВ鏋愭槸鍚︿负鏈夋晥JSON
    try:
        try:
            res=json.loads(s)
            return res
        except:
            res = eval(s)
            return res
    except:
        pass  # 涓嶆槸鏈夋晥鐨凧SON锛岄渶瑕佽繘涓€姝ュ�鐞�

    res=extract_json_part(s)
    if res is not None:
        return res
    else:
        # 鐢ㄥ皬鍐欑殑 true, false, null 鏇挎崲澶у啓鐨� True, False, None
        s = s.replace('True', 'true').replace('False', 'false').replace('None', 'null')

        # 浠庢彁渚涚殑瀛楃�涓蹭腑鎻愬彇JSON瀛楃�涓�
        # 璋冩暣姝ｅ垯琛ㄨ揪寮忎互姝ｇ‘鍖归厤```json寮€濮嬪埌```缁撴潫鐨勫唴瀹�
        # pattern = r'```json\n?({.*?})\n?```'
        pattern = r'```(?:json)?\n?([\s\S]*?)\n?```'
        match = re.search(pattern, s, re.DOTALL)

        if match:
            json_str = match.group(1)  # 鑾峰彇鍖归厤鍒扮殑JSON瀛楃�涓查儴鍒�
            # 灏濊瘯灏嗘彁鍙栫殑瀛楃�涓茶В鏋愪负JSON
            try:
                json_str=json_str.replace("\n","")
                json_str=json_str.replace("\'","'")
                json_obj = json.loads(json_str)
                return json_obj
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}")
                json_obj = robust_string_to_json2(json_str)
                print(json_obj)
                return json_obj
        else:
            print("娌℃湁鎵惧埌鍖归厤鐨凧SON鏁版嵁銆�")
            raise Exception("鏈�壘鍒版湁鏁��殑JSON瀛楃�涓�")



def extract_json_part(raw_output):
    """
    鎻愬彇 raw_output 涓�殑 JSON 閮ㄥ垎骞跺皢鍏惰В鏋愪负瀛楀吀銆�
    """
    try:
        # 浣跨敤姝ｅ垯琛ㄨ揪寮忓尮閰嶆墍鏈変互 '{' 寮€澶村苟浠� '}' 缁撴潫鐨勫唴瀹�
        # .*? 鏄�潪璐�┆妯″紡锛岀‘淇濆尮閰嶇�涓€涓�畬鏁寸殑 JSON 瀵硅薄
        json_match = re.search(r'({.*})', raw_output, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)  # 鑾峰彇鍖归��鐨� JSON 瀛楃�涓查儴鍒�

            # 灏濊瘯灏嗘彁鍙栫殑瀛楃�涓茶В鏋愪负 JSON
            try:
                json_obj = json.loads(json_str)
                return json_obj
            except json.JSONDecodeError as e:
                print(f"JSON瑙ｆ瀽閿欒�: {e}")

                # 灏濊瘯杩涗竴姝ュ�鐞嗭紝渚嬪�鍘婚櫎闈炴硶瀛楃�鎴栦慨姝ｆ牸寮�
                json_str = json_str.replace("\n", "").replace("\r", "").strip()
                json_str = re.sub(r",\s*}", "}", json_str)  # 鍘绘帀鏈€鍚庣殑澶氫綑閫楀彿
                json_str = re.sub(r",\s*]", "]", json_str)  # 鍘绘帀鏈€鍚庣殑澶氫綑閫楀彿
                
                try:
                    json_obj = json.loads(json_str)
                    return json_obj
                except json.JSONDecodeError as e:
                    print(f"杩涗竴姝�SON瑙ｆ瀽閿欒�: {e}")
                    return None
        else:
            print("JSON PARSE ERROR")
            return None

    except Exception as e:
        print(f"鎻愬彇JSON鏃跺彂鐢熼敊璇�: {repr(e)}")
        return None

def robust_string_to_json2(json_str):
    # Remove escape characters for double quotes
    json_str = json_str.replace('\\"', '"')
    
    # Replace single quotes with double quotes
    json_str = json_str.replace("'", '"')
    
    # Handle misplaced quotes inside the string
    json_str = re.sub(r'"\s*:\s*"', '": "', json_str)  # Ensure proper key-value formatting
    
    # Handle cases where quotes are used within values or keys
    json_str = re.sub(r'(?<=\w)"(?=\w)', '', json_str)  # Remove misplaced quotes between words
    
    # Ensure keys are quoted properly
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
    
    # Remove trailing commas before closing braces/brackets
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    
    return json_obj
