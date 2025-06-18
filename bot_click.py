import base64
import asyncio
import aiohttp
import argparse
import datetime
import urllib.parse
from asgiref.sync import sync_to_async
from db.init_db import insert_lot, get_active_records
from decouple import config

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

proxies = {
    config("PR").format(
        ip=config("PR_IP1"),
        port=config("PR_PORT1")
    ),
    config("PR").format(
        ip=config("PR_IP2"),
        port=config("PR_PORT2")
    ),
    config("PR").format(
        ip=config("PR_IP3"),
        port=config("PR_PORT3")
    ),
    config("PR").format(
        ip=config("PR_IP4"),
        port=config("PR_PORT4")
    ),
    config("PR").format(
        ip=config("PR_IP5"),
        port=config("PR_PORT5")
    ),
    config("PR").format(
        ip=config("PR_IP6"),
        port=config("PR_PORT6")
    ),
    config("PR").format(
        ip=config("PR_IP7"),
        port=config("PR_PORT7")
    ),
    config("PR").format(
        ip=config("PR_IP8"),
        port=config("PR_PORT8")
    ),
    config("PR").format(
        ip=config("PR_IP9"),
        port=config("PR_PORT9")
    ),
    config("PR").format(
        ip=config("PR_IP10"),
        port=config("PR_PORT10")
    ),
}


async def send_telegram_message(message):
    async with aiohttp.ClientSession() as session:
        telegram_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        chat = await sync_to_async(get_active_records)()
        payload = {
            'chat_id': chat[0].get("chat"),
            'text': message
        }
        async with session.post(telegram_url, json=payload) as response:
            if response.status != 200:
                await sync_to_async(logger.info)(f"Ошибка отправки уведомления: {await response.text()}")


async def authenticate_and_get_token(auth_url, payload):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(auth_url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                await sync_to_async(logger.info)(f"Получение токена --:{data.get('accessToken')}")
                return data.get('accessToken')
        except aiohttp.ClientError as e:
            await sync_to_async(logger.info)(f"HTTP error during authentication: {e}")
    return None


async def send_request(api_url, headers, proxy):
    import requests
    await sync_to_async(logger.info)(f"Отправляем запрос  --:{api_url, headers, proxy}")
    try:
        auth = HTTPProxyAuth(config("PR_USER"), config("PR_PASS"))
        prox = await sync_to_async(dict)()
        prox['http'] = proxy
        response = await asyncio.wait_for(
            sync_to_async(requests.get)(url=api_url, headers=headers, proxies=prox, auth=auth),
            timeout=2
        )
        #response = await sync_to_async(requests.get)(url=api_url, headers=headers, proxies=prox, auth=auth)
        await sync_to_async(logger.info)(f"Ответ --:{response}")
        await sync_to_async(response.raise_for_status)()
        return await sync_to_async(response.json)()
    except Exception as e:
        await sync_to_async(logger.info)(f"HTTP error occurred: {e} - Proxy: {proxy}")
    return None


async def take_tocken():
    token = await authenticate_and_get_token(AUTH_URL, AUTH_PAYLOAD)
    if token:
        await sync_to_async(logger.info)(f"Authorization: f'Bearer {token}'")
        return {"Authorization": f"Bearer {token}"}
    await sync_to_async(logger.info)("Failed to authenticate.")
    return None


async def take_orders(api_url, headers, curse, session, order_filter, proxy, timer):
    await sync_to_async(logger.info)(f"Начал брать ордера --:{api_url, headers, curse, session, order_filter, proxy}")
    while True:
        try:
            response = await send_request(api_url, headers, proxy)
            await sync_to_async(logger.info)(f"ЛОТЫ: {response.get('items')}")
            if await sync_to_async(response.get)('status_code') == 401:
                headers = await take_tocken()
                await sync_to_async(logger.info)(f"Получили новый токен: {headers}")
            count = 0
            for res in await sync_to_async(response.get)("items", []):
                to_time = await sync_to_async(res.get)("maxTimeoutAt")
                await sync_to_async(logger.info)(f"to_timeto_time: {to_time}")
                api_time =  await sync_to_async(datetime.datetime.fromisoformat)(to_time)
                await sync_to_async(logger.info)(f"api_timeapi_time: {api_time}")
                timer_at =  await sync_to_async(datetime.timedelta)(minutes=-await sync_to_async(int)(timer))
                await sync_to_async(logger.info)(f"timer_attimer_at: {timer_at}")
                api_time = api_time - timer_at
                tzinfo =  await sync_to_async(datetime.timezone)(datetime.timedelta(hours=5.0))
                await sync_to_async(logger.info)(f"tzinfotzinfo: {tzinfo}")
                now =  await sync_to_async(datetime.datetime.now)(tzinfo)
                if api_time > now:
                    continue
                if  await sync_to_async(res.get)("status") == "trader_payment":
                    count += 1
                    continue
                elif  await sync_to_async(res.get)("currencyRate") < curse and  await sync_to_async(res.get)("status") != "trader_payment" and count <= order_filter:
                    logger.info(f"Покупаем: {await sync_to_async(res.get)("currencyRate")}")
                    await buy(await sync_to_async(res.get)("id"), headers, session)
                    count += 1
        except Exception as e:
            await sync_to_async(logger.info)(f"Error while processing orders: {e}")
            await asyncio.sleep(1)


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
        logger.info(f"HTTP ошибка возникла: {http_err}")
        return {"error": str(http_err)}
    except Exception as err:
        logger.info(f"Произошла другая ошибка: {err}")
        return {"error": str(err)}


async def create_encoded_json(filter_int):
    await sync_to_async(logger.info)("POKUPKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    await sync_to_async(logger.info)(filter_int)
    if filter_int is None:
        return MONEY_FILTER_NO
    try:
        min_amount, max_amount = filter_int
    except Exception as e:
        await sync_to_async(logger.info)(f"Сломан фильр -- {filter_int} -- {e}")
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


async def buy(id, headers, session):
    try:
        async with session.post(ACCEPT_URL.format(id), headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            if result.get("status", None) == 'trader_payment':
                await sync_to_async(logger.info)(f"Куплен лот с айди:{id}")
                await send_telegram_message(f"КУПЛЕН ЛОТ С АЙДИ -- {id}")
                await sync_to_async(insert_lot)(lot_id=id)
            else:
                await sync_to_async(logger.info)(f"Не купили лот с айди:{id}")
                await sync_to_async(insert_lot)(lot_id=id, status=False)
    except aiohttp.ClientError as e:
        await sync_to_async(logger.info)(f"HTTP error during purchase: {e}")


async def main(args):
    while True:
        try:
            await sync_to_async(logger.info)("АРГУМЕНТЫ СТАРТА БОТА")
            await sync_to_async(logger.info)(args)
            headers = await take_tocken()
            if not headers:
                await sync_to_async(logger.info)("No token. Exiting.")
                return
            async with aiohttp.ClientSession() as session:
                pr = list(proxies)
                tasks = []
                for i in range(min(len(pr), args.processes)):
                    proxy = pr[i]
                    await sync_to_async(logger.info)(f"Прокси запущен в работу :{pr[i]}")
                    tasks.append(take_orders(await create_encoded_json(args.min_summ), headers, float(args.rate), session,
                                         int(args.order_filter), proxy, args.timer))
                await asyncio.gather(*tasks)
        except Exception as e:
            await sync_to_async(logger.info)(f"РЕСТАРТ :{args} ------- {e}")
            continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your script.")
    parser.add_argument("--rate", type=float, help="Введите значение курса.")
    parser.add_argument("--min_summ", type=str, help="Введите значение минимальной суммы.")
    parser.add_argument("--processes", type=int, help="Введите значение процессов.")
    parser.add_argument("--order_filter", type=int, help="Максимум заявок.")
    parser.add_argument("--timer", type=int, help="Таймер заявки.")
    asyncio.run(main(parser.parse_args()))
