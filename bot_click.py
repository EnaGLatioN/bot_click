import base64
import asyncio
import aiohttp
import argparse
from decouple import config
import logging
import requests
import urllib.parse
from asgiref.sync import sync_to_async
from db.init_db import insert_lot

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


async def authenticate_and_get_token(auth_url, payload):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(auth_url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('accessToken')
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during authentication: {e}")
    return None


async def send_request(api_url, headers, session):
    try:
        async with session.get(api_url, headers=headers) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error occurred: {e}")
    return None


async def take_tocken():
    token = await authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    if token:
        return {"Authorization": f"Bearer {token}"}
    logger.error("Failed to authenticate.")
    return None


async def take_orders(api_url, headers, curse, session, order_filter):
    while True:
        try:
            response = await send_request(api_url, headers, session)
            logger.info(f"ПРИШЕДШИЕ ЛОТЫ: {response}")
            count = 0
            logger.info(f"count count: {count}")
            for res in response.get("items", []):
                if res.get("status") == "trader_payment":
                    count += 1
                    logger.info(f"count count: {count}")
                elif res.get("currencyRate", float('inf')) < curse and res.get("status") != "trader_payment" and count <= order_filter:
                    await buy(res.get("id"), headers, session)
                    count += 1
        except Exception as e:
            logger.error(f"Error while processing orders: {e}")
            await asyncio.sleep(5)


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


async def create_encoded_json(filter_int):
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
        return MONEY_FILTER_OT.format(urllib.parse.quote(base64.b64encode(json_string.encode('utf-8')).decode('utf-8')))
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


async def buy(id, headers, session):
    try:
        async with session.post(ACCEPT_URL.format(id), headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            if result.get("status", None) == 'trader_payment':
                logger.info(f"Куплен лот с айди:{id}")
                await sync_to_async(insert_lot)(lot_id=id)
            else:
                logger.info(f"Не купили лот с айди:{id}")
                await sync_to_async(insert_lot)(lot_id=id, status=False)
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error during purchase: {e}")


async def main(args):
    logger.info("АРГУМЕНТЫ СТАРТА БОТА")
    logger.info(args)
    headers = await take_tocken()
    if not headers:
        logger.error("No token. Exiting.")
        return
    async with aiohttp.ClientSession() as session:
        tasks = [take_orders(await create_encoded_json(args.min_summ), headers, float(args.rate), session, int(args.order_filter)) for _ in range(args.processes)]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your script.")
    parser.add_argument("--rate", type=float, help="Введите значение курса.")
    parser.add_argument("--min_summ", type=str, help="Введите значение минимальной суммы.")
    parser.add_argument("--processes", type=int, help="Введите значение процессов.")
    parser.add_argument("--order_filter", type=int, help="Максимум заявок.")
    asyncio.run(main(parser.parse_args()))
