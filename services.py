from decouple import config
import logging
import requests


logger = logging.getLogger("my_bot_services")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("services.log")
file_handler.setLevel(logging.DEBUG)
file_logger_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_logger_format)

logger.addHandler(file_handler)


AUTH_URL = config("AUTH_URL", cast=str)
AUTH_PAYLOAD = {
    "email": config("MAIL", cast=str),
    "password": config("PASSWORD", cast=str)
}


def authenticate_and_get_token(auth_url, payload):
    try:
        response = requests.post(auth_url, json=payload)
        response.raise_for_status()
        return response.json().get('accessToken')
    except requests.exceptions.HTTPError as http_err:
        logger.info(f"HTTP error occurred during authentication: {http_err}")
        logger.info(f"Response content: {response.text}")
    except Exception as err:
        logger.info(f"Other error occurred during authentication: {err}")
    return None


def take_token():
    token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    headers = {
        "Authorization": f"Bearer {token}"
    }
    if token:
        return headers
    else:
        logger.info("Failed to authenticate.")
        return None
