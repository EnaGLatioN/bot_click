from decouple import config
import logging
import requests
from requests.auth import HTTPProxyAuth


logger = logging.getLogger("my_bot")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("bot.log")
file_handler.setLevel(logging.DEBUG)
file_logger_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_logger_format)

logger.addHandler(file_handler)


AUTH_URL = config("AUTH_URL", cast=str)
AUTH_PAYLOAD = {
    "email": config("MAIL", cast=str),
    "password": config("PASSWORD", cast=str)
}


def authenticate_and_get_token(auth_url, payload, proxy=None):
    try:
        if proxy is not None:
            auth = HTTPProxyAuth(config("PR_USER"), config("PR_PASS"))
            prox = dict()
            prox['http'] = proxy
            response = requests.post(url=auth_url, json=payload, proxies=prox, auth=auth)
        else:
            response = requests.post(auth_url, json=payload)
            response.raise_for_status()
        data =  response.json()
        logger.info(f"Получение токена --:{data.get('accessToken')}")
        return data.get('accessToken')
    except Exception as e:
       logger.info(f"HTTP error during authentication: {e}")
    return None


def take_token(proxy=None):
    if proxy is not None:
        token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD, proxy)
    else:
        token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    if token:
        logger.info(f"Authorization: f'Bearer {token}'")
        return {"Authorization": f"Bearer {token}"}
    logger.info("Failed to authenticate.")
    return None