import base64
import argparse
from decouple import config
import logging
import requests
import urllib.parse


logger = logging.getLogger("my_bot")
logger.setLevel(logging.DEBUG)

# Создаём обработчик для записи логов в файл
file_handler = logging.FileHandler("bot.log")
file_handler.setLevel(logging.DEBUG)
file_logger_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_logger_format)

# Добавляем обработчик к логгеру
logger.addHandler(file_handler)


AUTH_URL = config("AUTH_URL", cast=str)
AUTH_PAYLOAD = {
    "email": config("MAIL", cast=str),
    "password": config("PASSWORD", cast=str)
}

API_URL = config("API_URL", cast=str)
ORDER_URL = config("ORDER_URL", cast=str)

RATES_URL = config("RATES_URL", cast=str)

RATES = {"bybit", "", "[RUB] SBERBANK", "ByBit Tinkoff ", "Rapira", "Rapira minus ", "rapira"}

MONEY_FILTER_OT_DO = config("MONEY_FILTER_OT_DO", cast=str)
MONEY_FILTER_OT = config("MONEY_FILTER_OT", cast=str)
MONEY_FILTER_NO = config("MONEY_FILTER_NO", cast=str)

ACCEPT_URL = config("ACCEPT_URL", cast=str)


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


def send_request(api_url, headers):
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.info(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logger.info(f"Other error occurred: {err}")
    return None


def take_tocken():
    token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    headers = {
        "Authorization": f"Bearer {token}"
    }
    if token:
        return headers
    else:
        logger.info("Failed to authenticate.")
        return None


def take_orders(api_url, headers, curse):
    try:
        while True:
            try:
                response = requests.get(api_url, headers=headers)
                logger.info(f"ПРИШЕДШИЕ ЛОТЫ: {response.json()}")
                logger.info(f"проверка api_url : {api_url}")
                if response.status_code == 401:
                    logger.info(f"Получили новый токен: {response.json()}")
                    headers = take_tocken()
                for res in response.json().get("items", None):
                    if (res.get("currencyRate") < curse) and (res.get("status") != "trader_payment"):
                        buy(res.get("id"), headers)
            except Exception as e:
                logger.info(f"Что то не так: {e}")
                continue
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logger.error(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


def take_rates(rates_url, headers):
    curse = {}
    try:
        response = requests.get(rates_url, headers=headers)
        response.raise_for_status()
        count = 0
        for res in response.json():
            if res.get("source", None) in RATES and res.get("name", None) in RATES:
                count += 1
                curse[count] = f"{res.get('price', None)}"
        return curse
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logger.error(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


def create_encoded_json(filter_int):
    logger.info("POKUPKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    logger.info(filter_int)
    if filter_int is None:
        return MONEY_FILTER_NO
    try:
        min_amount, max_amount = filter_int
    except Exception as e:
        logger.info(f"Сломан фильр -- {filter_int} -- {e}")
        max_amount = None
        min_amount = filter_int
    if min_amount and max_amount is None:
        json_string = '{"minAmount":%s}' % (
            f"{min_amount}" if min_amount is not None else "null",
        )
        return MONEY_FILTER_OT.format(base64.b64encode(json_string.encode('utf-8')).decode('utf-8'))
    json_string = '{"minAmount":%s,"maxAmount":%s}' % (
        f"{min_amount}" if min_amount is not None else "null",
        f"{max_amount}" if max_amount is not None else "null"
    )
    return MONEY_FILTER_OT_DO.format(base64.b64encode(json_string.encode('utf-8')).decode('utf-8'))




def get_user_choice(rates):
    logger.info(f"Выберите нужный курс: {rates}")
    while True:
        try:
            choice = int(input("Введите номер курса: "))
            if choice in rates:
                return choice
            else:
                logger.info("Неверный номер. Пожалуйста, выберите номер из списка.")
        except ValueError:
            logger.error("Пожалуйста, введите корректный номер.")


def get_filters():
    while True:
        try:
            choice = str(input("Введите фильтры:"))
            if choice:
                return choice
            return None
        except ValueError:
            logger.error("Пожалуйста, введите корректный номер.")


def fix_filter(selected_filter):
    if selected_filter is not None:
        max_amount = None
        try:
            min_amount, max_amount = map(int, selected_filter.split('-'))
        except:
            min_amount = int(selected_filter)
        return min_amount, max_amount
    return None


def buy(id, headers):
    try:
        response = requests.post(ACCEPT_URL.format(id), headers=headers)
        response.raise_for_status()
        if response.json().get("status", None) == 'trader_payment':
            logger.info(f"Куплен лот с айди:{id}")
        else:
            logger.info(f"Не купили лот с айди:{id}")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logger.error(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


def main(args):
    logger.info("POKUPKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    logger.info(args)
    headers = take_tocken()
    if headers:
        take_orders(create_encoded_json(args.min_summ), headers, float(args.rate))
    else:
        logger.error(f"No token: {headers}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your script.")
    parser.add_argument("--rate", type=float, help="Введите значение курса.")
    parser.add_argument("--min_summ", type=str, help="Введите значение минимальной суммы.")
    main(parser.parse_args())
