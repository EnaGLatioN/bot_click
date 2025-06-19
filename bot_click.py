import base64
import argparse
import os
import datetime
import urllib.parse
from asgiref.sync import sync_to_async
from db.init_db import insert_lot, get_active_records
from decouple import config
import requests
from requests.auth import HTTPProxyAuth
import logging


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

API_URL = config("API_URL", cast=str)
ORDER_URL = config("ORDER_URL", cast=str)

RATES_URL = config("RATES_URL", cast=str)

RATES = {"bybit", "", "[RUB] SBERBANK", "ByBit Tinkoff ", "Rapira", "Rapira minus ", "rapira"}

MONEY_FILTER_OT_DO = config("MONEY_FILTER_OT_DO", cast=str)
MONEY_FILTER_OT = config("MONEY_FILTER_OT", cast=str)
MONEY_FILTER_NO = config("MONEY_FILTER_NO", cast=str)

ACCEPT_URL = config("ACCEPT_URL", cast=str)

TELEGRAM_BOT_TOKEN = config("TELE_TOCKEN", cast=str)


def send_telegram_message(message):
    try:
        telegram_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        chat = get_active_records()
        payload = {
            'chat_id': chat[0].get("chat"),
            'text': message
        }
        response = requests.post(telegram_url, json=payload)
        logger.info(f"Уведомление в телегу отправлено -- {response.json()}")
        response.raise_for_status()
    except Exception as e:
        logger.info(f"HTTP error: {e}")


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


def send_request(api_url, headers, proxy):
    import requests
    logger.info(f"Отправляем запрос  --:{api_url, headers, proxy}")
    try:
        auth = HTTPProxyAuth(config("PR_USER"), config("PR_PASS"))
        prox =dict()
        prox['http'] = proxy
        response = requests.get(url=api_url, headers=headers, proxies=prox, auth=auth, timeout=2.0)
        logger.info(f"Ответ --:{response}")
        return response.json()
    except Exception as e:
        logger.info(f"HTTP error occurred: {e} - Proxy: {proxy}")
    return None


def take_tocken(proxy=None):
    if proxy is not None:
        token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD, proxy)
    else:
        token = authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    if token:
        logger.info(f"Authorization: f'Bearer {token}'")
        return {"Authorization": f"Bearer {token}"}
    logger.info("Failed to authenticate.")
    return None


def take_orders(api_url, headers, curse, order_filter, proxy, timer):
    logger.info(f"Начал брать ордера --:{api_url, headers, curse, order_filter, proxy}")
    while True:
        try:
            response = send_request(api_url, headers, proxy)
            logger.info(f"ЛОТЫ: {response}")
            if response.get('statusCode', None) == 401:
                headers = take_tocken(proxy)
                logger.info(f"Получили новый токен: {headers}")
            count = 0
            logger.info(f"ДОШЛИ ДО ЦИКЛА")
            for res in response.get("items", []):
                api_time, now = time_to_time(timer, res)
                if  res.get("status") == "trader_payment":
                    count += 1
                    continue
                elif  res.get("currencyRate") < curse and res.get("status") != "trader_payment" and count <= order_filter and api_time > now:
                    logger.info(f"Покупаем: {res.get("currencyRate")}")
                    buy(res.get("id"), headers)
                    count += 1
        except Exception as e:
            logger.info(f"Error while processing orders: {e}")


def time_to_time(timer, res):
    try:
        to_time = res.get("maxTimeoutAt")
        logger.info(f"to_timeto_time: {to_time}")
        api_time = datetime.datetime.fromisoformat(to_time)
        logger.info(f"api_timeapi_time: {api_time}")
        timer_at = datetime.timedelta(minutes=-int(timer))
        logger.info(f"timer_attimer_at: {timer_at}")
        api_time = api_time - timer_at
        tzinfo = datetime.timezone(datetime.timedelta(hours=5.0))
        logger.info(f"tzinfotzinfo: {tzinfo}")
        now = datetime.datetime.now(tzinfo)
        return api_time, now
    except Exception as e:
        logger.info(f"Что то со временем: {e}")
        return None, None


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
    return MONEY_FILTER_OT_DO.format(urllib.parse.quote(base64.b64encode(json_string.encode('utf-8')).decode('utf-8')))


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
        result = response.json()
        if result.get("status", None) == 'trader_payment':
            logger.info(f"Куплен лот с айди:{id}")
            send_telegram_message(f"КУПЛЕН ЛОТ С АЙДИ -- {id}")
            sync_to_async(insert_lot)(lot_id=id)
        else:
            logger.info(f"Не купили лот с айди:{id}")
            insert_lot(lot_id=id, status=False)
    except Exception as e:
        logger.info(f"HTTP error during purchase: {e}")


def main(args):
    while True:
        try:
            logger.info("АРГУМЕНТЫ СТАРТА БОТА")
            logger.info(args)
            headers = take_tocken(args.proxy)
            if not headers:
                logger.info("No token. Exiting.")
                return
            logger.info(f"Прокси запущен в работу :{args.proxy}")
            take_orders(create_encoded_json(args.min_summ), headers, float(args.rate),int(args.order_filter), args.proxy, args.timer)
        except Exception as e:
            logger.info(f"Что то с мэйн -- :{e}")
            continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your script.")
    parser.add_argument("--rate", type=float, help="Введите значение курса.")
    parser.add_argument("--min_summ", type=str, help="Введите значение минимальной суммы.")
    parser.add_argument("--processes", type=int, help="Введите значение процессов.")
    parser.add_argument("--order_filter", type=int, help="Максимум заявок.")
    parser.add_argument("--timer", type=int, help="Таймер заявки.")
    parser.add_argument("--proxy", type=str, help="Прокси процесса.")
    main(parser.parse_args())

