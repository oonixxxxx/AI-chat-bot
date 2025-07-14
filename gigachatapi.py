import streamlit as st
import requests
import uuid
import base64
from io import BytesIO
from bs4 import BeautifulSoup
from PIL import Image
from time import sleep
import random

# Настройки API
CLIENT_ID = ''
SECRET = ''
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"

# Получение токена
def get_access_token():
    """
    Получает токен доступа для GigaChat API через OAuth-аутентификацию.

    Отправляет POST-запрос на сервер авторизации с использованием клиентских учетных данных.
    Генерирует уникальный идентификатор запроса (RqUID) и передает область доступа "GIGACHAT_API_PERS".
    Требует предварительного установления переменных окружения:
    - CLIENT_ID: Идентификатор клиента
    - SECRET: Секретный ключ клиента (в формате "id:secret")

    Возвращает:
        str|None: Токен доступа в виде строки, если запрос успешен, иначе None

    Исключения:
        При сетевых проблемах или ошибочных ответах сервера выводит сообщение об ошибке
        в консоль и возвращает None вместо возбуждения исключения

    Примечание:
        Использует неявную отключение проверки SSL-сертификата (verify=False),
        что может представлять риск безопасности в продакшен-средах
    """
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4())
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, SECRET.split(':')[1])
    try:
        response = requests.post(url, headers=headers, data=data, auth=auth, verify=False)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        print(f"Ошибка при получении токена: {str(e)}")
        return None


# Генерация изображения
def generate_image(prompt: str, access_token: str):
    """
    Генерирует изображение через GigaChat API на основе текстового описания.

    Отправляет запрос к модели GigaChat с ролью художника, которая создает изображения по текстовым описаниям.
    Обрабатывает HTML-ответ API для извлечения ссылки на сгенерированное изображение и загружает его.

    Параметры:
        prompt (str): Текстовое описание изображения, которое необходимо сгенерировать
        access_token (str): Токен доступа для авторизации в GigaChat API

    Возвращает:
        PIL.Image|None: Объект изображения в формате PIL, если генерация успешна, иначе None

    Исключения:
        Ловит все исключения при выполнении HTTP-запросов и выводит ошибку через Streamlit,
        возвращает None вместо прерывания выполнения

    Примечание:
        - Использует метод BeautifulSoup для парсинга HTML-ответа API
        - Загружает изображение по сгенерированной ссылке
        - Отключение проверки SSL-сертификата (verify=False) может быть небезопасным
        - Требует установленных библиотек: requests, beautifulsoup4, pillow
    """
    url = f"{GIGACHAT_API_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": "Ты — художник, который создает изображения по описанию."},
            {"role": "user", "content": prompt}
        ],
        "function_call": "auto"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        soup = BeautifulSoup(content, "html.parser")
        img_tag = soup.find("img")
        if not img_tag:
            return None
        
        file_id = img_tag["src"]
        image_url = f"{GIGACHAT_API_URL}/files/{file_id}/content"
        image_response = requests.get(image_url, headers=headers, verify=False)
        image_response.raise_for_status()
        
        return Image.open(BytesIO(image_response.content))
    except Exception as e:
        st.error(f"Ошибка при генерации изображения: {str(e)}")
        return None


# Отправка текстового запроса
def send_prompt(prompt: str, access_token: str):
    """
    Отправляет запрос в GigaChat API для генерации текста или изображения в зависимости от содержимого промпта.

    Проверяет наличие ключевых слов, связанных с генерацией изображений (например, "нарисуй", "изображение").
    Если такие слова найдены, вызывает функцию generate_image(). В противном случае отправляет текстовый запрос.

    Параметры:
        prompt (str): Текст пользователя, содержащий запрос на генерацию текста или изображения
        access_token (str): Токен доступа для авторизации в GigaChat API

    Возвращает:
        Union[PIL.Image, str, None]: 
            - Объект изображения (PIL.Image) при запросе генерации изображения
            - Строка текстового ответа при текстовом запросе
            - None в случае ошибки

    Логика работы:
        1. Выполняет анализ промпта на предмет наличия ключевых слов
        2. При необходимости генерации изображения вызывает generate_image()
        3. Для текстовых запросов отправляет POST-запрос к /chat/completions endpoint
        4. Использует параметр temperature=0.7 для контроля случайности ответа

    Исключения:
        Все ошибки обрабатываются через Streamlit (st.error()), 
        вместо возбуждения исключений возвращается None
    """
    # Проверяем, нужно ли генерировать изображение
    if any(word in prompt.lower() for word in ["нарисуй", "изображение", "картинк", "нарисуйте"]):
        return generate_image(prompt, access_token)
    else:
        url = f"{GIGACHAT_API_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            st.error(f"Ошибка при запросе к GigaChat: {str(e)}")
            return None


# Настройка страницы
st.set_page_config(
    page_title="AI Чат-бот с генерацией изображений",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стили CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# Инициализация сессии
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Привет! Я ваш AI помощник. Могу ответить на вопросы или нарисовать картинку по вашему описанию 😊"}]

# Заголовок
st.markdown("""
    <div class="header">
        <h1 style='text-align: center; color: #4a4a4a;'>
            <span style='color: #6e48aa;'>AI</span> Чат-бот с генерацией изображений
        </h1>
        <p style='text-align: center; color: #7a7a7a;'>
            Ваш интеллектуальный помощник на базе GigaChat
        </p>
    </div>
""", unsafe_allow_html=True)

# Получение токена
if "access_token" not in st.session_state:
    with st.spinner("🔐 Устанавливаем безопасное соединение..."):
        st.session_state.access_token = get_access_token()
        if not st.session_state.access_token:
            st.error("Не удалось получить токен доступа. Проверьте настройки.")
            st.stop()
        sleep(1)

# Боковая панель
with st.sidebar:
    st.markdown("## 📌 О чат-боте")
    st.markdown("""
    Это интеллектуальный помощник на базе GigaChat API. 
    Вы можете:
    - Задавать любые вопросы
    - Генерировать изображения (начните запрос со слов "нарисуй")
    """)
    st.markdown("---")
    st.markdown("🛠️ Разработано с ❤️ для вас")

# Контейнер для чата
chat_container = st.container()

# Анимация ввода сообщения
def animate_message(message, role, is_image=False):
    """
    Анимирует отображение сообщения в интерфейсе чата с эффектом постепенного появления текста
    или прямого отображения изображения в зависимости от параметров.

    Функция реализует два режима работы:
    1. Для текстовых сообщений - последовательное появление слов с задержкой
    2. Для изображений - прямое отображение без анимации

    Параметры:
        message (Union[str, PIL.Image]): Содержимое сообщения (текст или изображение)
        role (str): Роль отправителя ("user" или "assistant")
        is_image (bool): Флаг, указывающий на необходимость отображения изображения

    Возвращает:
        str: Полный текст сообщения после завершения анимации

    Особенности реализации:
        - Для пользовательских сообщений (role="user") используется более быстрая анимация (0.05с)
        - Для ответов ассистента (role="assistant") применяется медленная анимация (0.03с)
        - При is_image=True использует st.image() для отображения изображения
        - Зависит от CSS-классов (.user-message, .assistant-message, .message-content) для стилизации
    """
    with chat_container:
        if role == "user":
            message_placeholder = st.empty()
            full_response = ""
            for chunk in message.split():
                full_response += chunk + " "
                sleep(0.05)
                message_placeholder.markdown(f"""
                <div class="user-message">
                    <div class="message-content">
                        {full_response}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            if is_image:
                st.image(message, use_column_width=True)
            else:
                message_placeholder = st.empty()
                full_response = ""
                for chunk in message.split():
                    full_response += chunk + " "
                    sleep(0.03)
                    message_placeholder.markdown(f"""
                    <div class="assistant-message">
                        <div class="message-content">
                            {full_response}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        return full_response


# Отображение истории сообщений
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <div class="message-content">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            if isinstance(message["content"], Image.Image):  # Если это изображение
                st.image(message["content"], caption="Сгенерированное изображение")
            else:
                st.markdown(f"""
                <div class="assistant-message">
                    <div class="message-content">
                        {message["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# Обработка ввода пользователя
if prompt := st.chat_input("Введите ваш вопрос или 'нарисуй...'..."):
    # Анимация ввода пользователя
    user_message = animate_message(prompt, "user")
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Определяем тип запроса
    is_image_request = any(word in prompt.lower() for word in ["нарисуй", "изображение", "картинк"])
    
    if is_image_request:
        with st.spinner("🎨 Создаю изображение..."):
            response = send_prompt(prompt, st.session_state.access_token)
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Не удалось сгенерировать изображение 😢"})
    else:
        typing_emojis = ["✍️", "💭", "🧠", "🤔", "⌨️"]
        with st.spinner(f"{random.choice(typing_emojis)} Обрабатываю ваш запрос..."):
            response = send_prompt(prompt, st.session_state.access_token)
            if response:
                assistant_message = animate_message(response, "assistant")
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Произошла ошибка при обработке запроса"})
