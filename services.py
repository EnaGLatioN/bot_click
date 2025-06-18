from decouple import config
import logging
import requests
from requests.auth import HTTPProxyAuth


logger = logging



AUTH_URL = config("AUTH_URL", cast=str)
AUTH_PAYLOAD = {
    "email": config("MAIL", cast=str),
    "password": config("PASSWORD", cast=str)
}
RATES_URL = config("RATES_URL", cast=str)

RATES = {"bybit", "", "[RUB] SBERBANK", "ByBit Tinkoff ", "Rapira", "Rapira minus ", "rapira"}


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
        print("TOOOOOOOOOOOOOOOOOOOKEN", data.get('accessToken'))
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


def take_rates(rates_url, headers, proxy=None):
    curse = {}
    try:
        if proxy is not None:
            auth = HTTPProxyAuth(config("PR_USER"), config("PR_PASS"))
            prox = dict()
            prox['http'] = proxy
            response = requests.get(url=rates_url, headers=headers, proxies=prox, auth=auth)
            response.raise_for_status()
        else:
            response = requests.get(rates_url, headers=headers)
            response.raise_for_status()
        count = 0
        for res in response.json():
            if res.get("source", None) in RATES and res.get("name", None) in RATES:
                count += 1
                curse[count] = f"{res.get('price', None)}"
        return curse
    except requests.exceptions.HTTPError as http_err:
        logger.info(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logger.info(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}