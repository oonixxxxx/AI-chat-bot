'''
curl -L -X POST 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth' \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Accept: application/json' \
-H 'RqUID: <идентификатор_запроса>' \
-H 'Authorization: Basic ключ_авторизации' \
--data-urlencode 'scope=GIGACHAT_API_PERS'
'''
import streamlit as st
import requests
import uuid
import base64
from requests.auth import HTTPBasicAuth

CLIENT_ID = 'client id'
SECRET = 'secret code'
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"

import requests
from requests.auth import HTTPBasicAuth

def get_access_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": "6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e",  # Можно оставить как есть или генерировать
    }
    
    data = {
        "scope": "GIGACHAT_API_PERS",
    }
    
    auth = HTTPBasicAuth(CLIENT_ID, SECRET.split(':')[1])
    
    response = requests.post(url, headers=headers, data=data, auth=auth, verify=False)
    return response.json().get("access_token")

def send_prompt(message: str, access_token: str) -> str:
    """Отправляет сообщение в GigaChat и получает ответ"""
    if not access_token:
        return "Ошибка: отсутствует токен доступа"
        
    url = f"{GIGACHAT_API_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            url=url,
            headers=headers,
            json=payload,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Ошибка при запросе к GigaChat: {str(e)}")
        if hasattr(e, 'response') and e.response:
            st.error(f"Детали ошибки: {e.response.text}")
        return "Извините, произошла ошибка"

def send_promt_and_get_result():
    pass

def get_image():
    pass


# Стили CSS для улучшения внешнего вида
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")  #