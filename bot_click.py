import base64
import logging
import asyncio
import aiohttp
import requests
import argparse

import urllib.parse
from asgiref.sync import sync_to_async
from db.init_db import insert_lot, get_active_records
from decouple import config
from requests.auth import HTTPProxyAuth


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


async def send_telegram_message(message, mail):
    async with aiohttp.ClientSession() as session:
        chat = await sync_to_async(get_active_records)()
        payload = {
            'chat_id': chat[0].get("chat"),
            'text': message
        }
        async with session.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage', json=payload) as response:
            if response.status != 200:
                logging.info(f"Ошибка отправки уведомления: {await response.text()}")


async def authenticate_and_get_token(auth_url, payload, proxy):
    logging.info(f"Получаем токен --:{auth_url, payload, proxy}")
    try:
        prox = await sync_to_async(dict)()
        prox['http'] = proxy
        response = await sync_to_async(requests.post)(url=auth_url,json=payload, proxies=prox, auth=HTTPProxyAuth(config("PR_USER"), config("PR_PASS")))
        data = await sync_to_async(response.json)()
        return data.get('accessToken')
    except aiohttp.ClientError as e:
        logging.info(f"HTTP error during authentication: {e}")


async def send_request(api_url, headers, proxy):
    logging.info(f"Отправляем запрос  --:{api_url, headers, proxy}")
    try:
        prox = await sync_to_async(dict)()
        prox['http'] = proxy
        response = await sync_to_async(requests.get)(
            url=api_url,
            headers=headers,
            proxies=prox,
            auth=HTTPProxyAuth(config("PR_USER"), config("PR_PASS")))
        return await sync_to_async(response.json)()
    except Exception as e:
        logging.info(f"HTTP error occurred: {e} - Proxy: {proxy}")



async def take_tocken(proxy, email, password):
    auth_payload = {
        "email": email,
        "password": password
    }
    token = await authenticate_and_get_token(AUTH_URL, auth_payload, proxy)
    return {"Authorization": f"Bearer {token}"}


async def take_orders(api_url, curse, proxy, email, password, headers):
    logging.info(f"Начал брать ордера --:{api_url, headers, curse, proxy}")
    if not headers:
        logging.info("No token. Exiting.")
    while True:
        try:
            response = await send_request(api_url, headers, proxy)
            logging.info(f"ЛОТЫ: {response.get('items')}")
            if response.get('statusCode', None) == 401:
                headers = await take_tocken(proxy, email, password)
                logging.info(f"NNNNNNNNNNNNNNNNNEEEEEEEEEEEEEWWWWWWWWWWWWW TTTTTTTTTTOOOOOOOKKKKKKEEENNNN: {headers}")
            for res in response.get("items", []):
                if  await sync_to_async(res.get)("status") == "trader_payment":
                    continue
                if res.get("currencyRate") <= curse :
                    await buy(res.get("id"), proxy, email, headers)
        except Exception as e:
            logging.info(f"Error while processing orders: {e}")
            continue


def take_rates(rates_url, headers):
    import requests
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
        print(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        print(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


async def create_encoded_json(filter_int):
    logging.info("POKUPKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    logging.info(filter_int)
    if filter_int is None:
        return MONEY_FILTER_NO
    try:
        min_amount, max_amount = filter_int
    except Exception as e:
        logging.info(f"Сломан фильр -- {filter_int} -- {e}")
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



async def buy(id, proxy, mail, headers):
    try:
        prox = await sync_to_async(dict)()
        prox['http'] = proxy
        response = await sync_to_async(requests.post)(
            url=ACCEPT_URL.format(id),
            headers=headers,
            proxies=prox,
            auth=HTTPProxyAuth(config("PR_USER"), config("PR_PASS"))
            )
        result = await sync_to_async(response.json)()
        if result.get("status") == 'trader_payment':
            await send_telegram_message(f"КУПЛЕН ЛОТ С АЙДИ -- {id}", mail)
            await sync_to_async(insert_lot)(lot_id=id, status=True)
            logging.info(f"Куплен лот с айди:{id}")
        else:
            logging.info(f"Не купили лот с айди:{id}")
            await sync_to_async(insert_lot)(lot_id=id, status=False)
    except aiohttp.ClientError as e:
        logging.info(f"HTTP error during purchase: {e}")


async def main(args):
    logging.info(f"АРГУМЕНТЫ СТАРТА БОТА--{args}")
    headers = await take_tocken(args.proxy, args.email, args.password)
    await asyncio.gather(take_orders(await create_encoded_json(args.min_summ), float(args.rate), args.proxy, args.email, args.password, headers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your script.")
    parser.add_argument("--rate", type=float, help="Введите значение курса.")
    parser.add_argument("--min_summ", type=str, help="Введите значение минимальной суммы.")
    parser.add_argument("--processes", type=int, help="Введите значение процессов.")
    parser.add_argument("--proxy", type=str, help="Таймер заявки.")
    parser.add_argument("--email", type=str, help="email")
    parser.add_argument("--password", type=str, help="password")
    asyncio.run(main(parser.parse_args()))
