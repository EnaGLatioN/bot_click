import requests
import time
import logging
import base64
import json
import re
import urllib.parse
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

AUTH_URL = "https://gfhbgfbtre.com/api/auth/login"
AUTH_PAYLOAD = {
    "email": "skotradde@gmail.com",
    "password": "jCoQ@#WcnD7oWHGj"
}

API_URL = "https://gfhbgfbtre.com/api/users/me"
ORDER_URL = "https://gfhbgfbtre.com/api/payout-orders/trader/active?page=1&take=5&countAs=none"

RATES_URL = "https://gfhbgfbtre.com/api/currency-exchange/rates"
RATES = {"bybit", "", "[RUB] SBERBANK", "ByBit Tinkoff ", "Rapira", "Rapira minus ", "rapira"}

MONEY_FILTER_OT_DO = "https://gfhbgfbtre.com/api/payout-orders/trader/active?filters={}&page=1&take=5&countAs=none"
MONEY_FILTER_OT = "https://gfhbgfbtre.com/api/payout-orders/trader/active?filters={}&page=1&take=5&countAs=none"
MONEY_FILTER_NO = "https://gfhbgfbtre.com/api/payout-orders/trader/active?page=1&take=5&countAs=none"
ACCEPT_URL = "https://gfhbgfbtre.com/api/payout-orders/trader/{}/accept"


def authenticate_and_get_token(auth_url, payload):
    try:
        response = requests.post(auth_url, json=payload)
        response.raise_for_status()
        token = response.json().get('accessToken')
        return token
    except requests.exceptions.HTTPError as http_err:
        logging.info(f"HTTP error occurred during authentication: {http_err}")
        logging.info(f"Response content: {response.text}")
    except Exception as err:
        logging.info(f"Other error occurred during authentication: {err}")
    return None


def send_request(api_url, headers):
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logging.info(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logging.info(f"Other error occurred: {err}")
    return None


def take_tocken():
    token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    headers = {
        "Authorization": f"Bearer {token}"
    }
    if token:
        return headers
    else:
        logging.info("Failed to authenticate.")
        return None


def take_orders(api_url, headers, curse):
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        while True:
            for res in response.json().get("items", None):
                if res.get("currencyRate") < curse:
                    buy(res.get("id"), headers)
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logging.error(f"Произошла другая ошибка: {err}")
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
                curse[count] = f"{res.get("price", None)}"
        return curse
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logging.error(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


def create_encoded_json(filter_int):
    if filter_int is None:
        return MONEY_FILTER_NO
    min_amount, max_amount = filter_int
    if min_amount and max_amount is None:
        json_string = '{"minAmount":%s}' % (
            f"{min_amount}" if min_amount is not None else "null",
        )
        url_encoded = urllib.parse.quote(base64.b64encode(json_string.encode('utf-8')).decode('utf-8'))
        return MONEY_FILTER_OT.format(url_encoded)
    json_string = '{"minAmount":%s,"maxAmount":%s}' % (
        f"{min_amount}" if min_amount is not None else "null",
        f"{max_amount}" if max_amount is not None else "null"
    )
    url_encoded = urllib.parse.quote(base64.b64encode(json_string.encode('utf-8')).decode('utf-8'))
    return MONEY_FILTER_OT_DO.format(url_encoded)




def get_user_choice(rates):
    logging.info(f"Выберите нужный курс: {rates}")
    while True:
        try:
            choice = int(input("Введите номер курса: "))
            if choice in rates:
                return choice
            else:
                logging.info("Неверный номер. Пожалуйста, выберите номер из списка.")
        except ValueError:
            logging.error("Пожалуйста, введите корректный номер.")

def get_filters():
    while True:
        try:
            choice = str(input("Введите фильтры:"))
            if choice:
                return choice
            return None
        except ValueError:
            logging.error("Пожалуйста, введите корректный номер.")


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
        accept = response.json()
        if accept.get("status", None) == 'trader_payment':
            logging.info(f"Куплен лот с айди:{id}")
        logging.info(f"Купить лот с айди:{id}  не удалось")
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logging.error(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


def main():
    headers = take_tocken()
    if headers:
        rates = take_rates(RATES_URL, headers)
        user_choice = get_user_choice(rates)
        selected_rate = rates[user_choice]
        selected_filter = get_filters()
        logging.info(f"Вы выбрали курс: {selected_rate}")
        filter_int = fix_filter(selected_filter)
        logging.info(f"Вы выбрали фильтр от: {filter_int}")
        take_orders(create_encoded_json(filter_int), headers, float(selected_rate))
    else:
        logging.error(f"No token: {headers}")

if __name__ == "__main__":
    main()
