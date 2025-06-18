import logging
import subprocess
import os
import signal

import telebot
from telebot.types import ReplyKeyboardRemove, CallbackQuery
from decouple import config

from services import take_token
from bot_click import (
    RATES_URL,
    take_rates,
)
from db.init_db import (
    insert_positions,
    create_connection,
    update_positions,
    get_active_records,
    insert_process,
    update_processes,
    get_active_processes
)

# TELE_TOCKEN = "8094728804:AAHdXxJZ00MUlCaZaRdiRIv35yYUWtWHkJI"

bot = telebot.TeleBot(config("TELE_TOCKEN", cast=str))
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

@bot.message_handler(commands=['start',])
def send_welcome(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "Да", 
            callback_data="start-bot"
        ),
        telebot.types.InlineKeyboardButton(
            "Нет", 
            callback_data="goodbay"
        ),
        telebot.types.InlineKeyboardButton(
            "Завершить все процессы?",
            callback_data="finish-parse"
        ),
    )
    bot.reply_to(message, "Запустить бота?", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "start-bot")
def start_bot(call: CallbackQuery):
    chat_id = call.message.chat.id
    print(f"Chat111111111111 ID: {chat_id}")
    rates = take_rates(RATES_URL, take_token())
    keyboard = telebot.types.InlineKeyboardMarkup()
    for i in rates.values():
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                i, 
                callback_data=f"take-rates-{i}"
            ),
        )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите курс",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("take-rates"))
def callback_inline(call: CallbackQuery):
    rate = call.data.replace("take-rates-", "")
    chat_id = call.message.chat.id
    if not get_active_records(connection=create_connection()):
        insert_positions(
            connection=create_connection(),
            min_summ=0,
            rate=rate,
            disperce=0,
            chat=chat_id
        )
    else:
        update_positions(connection=create_connection(), rate=rate, chat=chat_id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Введите минимальную сумму",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("dispersion-minus"))
def callback_inline(call: CallbackQuery):
    dispersion = float(call.data.replace("dispersion-minus-", "")) - 0.1
    keyboard = telebot.types.InlineKeyboardMarkup()
    if dispersion > 0:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "-", 
                callback_data=f"dispersion-minus-{dispersion}"
            ),
            telebot.types.InlineKeyboardButton(
                "+", 
                callback_data=f"dispersion-plus-{dispersion}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "Готово", 
                callback_data=f"dispersion-ready-{dispersion}"
            ),
        )
    else:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "+", 
                callback_data=f"dispersion-plus-{dispersion}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "Готово", 
                callback_data=f"dispersion-ready-{dispersion}"
            ),
        )
    curse = get_active_records(connection=create_connection())[0].get("rate", None)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Отклонение от курса: {dispersion}% (max: {curse + (curse * dispersion / 100)})",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("dispersion-plus"))
def callback_inline(call: CallbackQuery):
    dispersion = float(call.data.replace("dispersion-plus-", "")) + 0.1
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "-", 
            callback_data=f"dispersion-minus-{dispersion}"
        ),
        telebot.types.InlineKeyboardButton(
            "+", 
            callback_data=f"dispersion-plus-{dispersion}"
        ),
    ).row(
        telebot.types.InlineKeyboardButton(
            "Готово", 
            callback_data=f"dispersion-ready-{dispersion}"
        ),
    )
    curse = get_active_records(connection=create_connection())[0].get("rate", None)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Отклонение от курса: {dispersion}% (max: {curse + (curse * dispersion / 100)})",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("dispersion-ready"))
def callback_inline(call: CallbackQuery):
    dispersion = float(call.data.replace("dispersion-ready-", ""))
    keyboard = telebot.types.InlineKeyboardMarkup()
    record = {}
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "Далее выбор кол-ва заявок и процессов.",
            callback_data=f"start-parse"
        ),
    )
    if len(get_active_records(create_connection())) == 1:
        record = get_active_records(create_connection())[0]
    else:
        logging.error("В базе больше одной активной записи.")
    curse = get_active_records(connection=create_connection())[0].get("rate", None)

    update_positions(
        connection=create_connection(),
        disperce=curse + (curse * dispersion / 100),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Курс: {record.get("rate", None)}\nМин. сумма: {record.get("min_summ", None)}\nОтклонение от курса: {dispersion}% (max: {curse + (curse * dispersion / 100)})",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "ready-parce")
def start_bot(call: CallbackQuery):
    curse = 0
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "-",
            callback_data=f"processes-minus-{1}"
        ),
        telebot.types.InlineKeyboardButton(
            "+",
            callback_data=f"processes-plus-{1}"
        ),
    ).row(
        telebot.types.InlineKeyboardButton(
            "ДАЛЕЕ",
            callback_data=f"processes-ready-{1}"
        ),
    )
    bot.send_message(
        chat_id=call.from_user.id,
        text=f"Процессов будет запущено - {curse}",
        reply_markup=keyboard
    )
    return


@bot.callback_query_handler(func=lambda call: call.data.startswith("processes-minus"))
def callback_inline(call: CallbackQuery):
    dispersion = int(call.data.replace("processes-minus-", "")) - 1
    keyboard = telebot.types.InlineKeyboardMarkup()
    if dispersion > 0:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "-",
                callback_data=f"processes-minus-{dispersion}"
            ),
            telebot.types.InlineKeyboardButton(
                "+",
                callback_data=f"processes-plus-{dispersion}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "Готово",
                callback_data=f"processes-ready-{dispersion}"
            ),
        )
    else:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "+",
                callback_data=f"processes-plus-{dispersion}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "ДАЛЕЕ",
                callback_data=f"processes-ready-{dispersion}"
            ),
        )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Процессов будет запущено - {dispersion}",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("processes-plus"))
def callback_inline(call: CallbackQuery):
    dispersion = int(call.data.replace("processes-plus-", "")) + 1
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "-",
            callback_data=f"processes-minus-{dispersion}"
        ),
        telebot.types.InlineKeyboardButton(
            "+",
            callback_data=f"processes-plus-{dispersion}"
        ),
    ).row(
        telebot.types.InlineKeyboardButton(
            "ДАЛЕЕ",
            callback_data=f"processes-ready-{dispersion}"
        ),
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Процессов будет запущено - {dispersion}",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("processes-ready"))
def start_bot(call: CallbackQuery):
    processes = int(call.data.replace("processes-ready-", ""))
    update_positions(connection=create_connection(), num_proc=processes)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Введите таймер целым числом от 1 до 999",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("proc-start"))
def start_bot(call: CallbackQuery):
    processes = int(call.data.replace("proc-start-", ""))
    keyboard = telebot.types.InlineKeyboardMarkup()
    record = {}
    records_to_insert = []
    try:
        if len(get_active_records(create_connection())) == 1:
            record = get_active_records(create_connection())[0]
        else:
            logging.error("В базе больше одной активной записи.")
        print("DDDDDDDDDDDDDDDDDD")
        print(record)
        #TODO добавь тут процессы
        pr = list(proxies)
        for i in range(min(len(pr), processes)):
            proxy = pr[i]
            print("ASSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS")
            active_process = subprocess.Popen(
                ["poetry", "run", "python", "bot_click.py",
                 "--rate", str(record.get("disperce")),
                 "--min_summ", str(record.get("min_summ")),
                 "--processes", str(processes),
                 "--order_filter", str(record.get("order_filter")),
                 "--timer",  str(record.get("timer")),
                 "--proxy", proxy,
                 ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(proxy)
            print(active_process)
            records_to_insert.append((
                f"poetry run python bot_click.py --rate {str(record.get('disperce'))} --min_summ {str(record.get('min_summ'))} --processes {str(processes)} --order_filter {str(record.get('order_filter'))}",
                active_process.pid
            ))
            logging.info("Процесс запущен.")
        print("LLLLLLLLLLLLLLLLLLLLLLLLLLLL")
        logging.info(records_to_insert)

        insert_process(create_connection(), records_to_insert)
        # active_process = subprocess.Popen(
        #     ["python", "bot_click.py",
        #      "--rate", str(record.get("disperce")),
        #      "--min_summ", str(record.get("min_summ")),
        #      "--processes", str(processes),
        #      "--order_filter", str(record.get("order_filter")),
        #       "--timer",  str(record.get("timer")),
        #      ],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        #     text=True
        # )

    except Exception as e:
        logging.error(f"Ошибка при запуске команды: {e}")
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "Остановить", 
            callback_data=f"finish-parse"
        ),
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Бот запущен",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "finish-parse")
def start_bot(call: CallbackQuery):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "Да", 
            callback_data="start-bot"
        ),
        telebot.types.InlineKeyboardButton(
            "Нет", 
            callback_data="goodbay"
        ),
    )
    for process in get_active_processes(create_connection()):
        try:
            pid = process.get("pid")
            os.kill(pid, signal.SIGTERM)
            logging.info(f"Процесс с PID {pid} успешно завершен.")
        except OSError as e:
            logging.info(f"Ошибка при попытке завершения процесса с PID {pid}: {e}")
    update_processes(create_connection())

    update_positions(
        connection=create_connection(),
        status=False,
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Бот остановлен\nЗапустить заново?",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data == "goodbay")
def start_bot(call: CallbackQuery):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="До скорых встреч!",
    )


@bot.message_handler(content_types=['text'])
def take_min_amount(message):
    if message.json.get("text").isdigit() and int(message.json.get("text")) > 1000:
        update_positions(
            connection=create_connection(),
            min_summ=int(message.json.get("text")),
        )
        curse = get_active_records(connection=create_connection())[0].get("rate", None)
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "-", 
                callback_data=f"dispersion-minus-{0.1}"
            ),
            telebot.types.InlineKeyboardButton(
                "+", 
                callback_data=f"dispersion-plus-{0.1}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "Готово", 
                callback_data=f"dispersion-ready-{0.1}"
            ),
        )
        bot.send_message(
            chat_id=message.from_user.id,
            text=f"Отклонение от курса: {0.1}% (max: {curse + (curse * 0.1 / 100)})",
            reply_markup=keyboard
        )
        return

    if int(message.json.get("text")) < 1000:
        active = get_active_records(connection=create_connection())
        keyboard = telebot.types.InlineKeyboardMarkup()
        update_positions(connection=create_connection(), timer=int(message.json.get("text")))
        keyboard.row(
        ).row(
            telebot.types.InlineKeyboardButton(
                "ЗАПУСК",
                callback_data=f"proc-start-{active[0].get('num_proc')}"
            ),
        )
        bot.send_message(
            chat_id=message.from_user.id,
            text=f"Вы выбрали таймер {message.json.get('text')}",
            reply_markup=keyboard
        )
        return
    bot.send_message(
        chat_id=message.from_user.id,
        text=f"Неверный формат данных, попробуй ещё раз",
        reply_markup=ReplyKeyboardRemove()
    )


@bot.callback_query_handler(func=lambda call: call.data == "start-parse")
def start_bot(call: CallbackQuery):
    curse = 0
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "-",
            callback_data=f"order-minus-{1}"
        ),
        telebot.types.InlineKeyboardButton(
            "+",
            callback_data=f"order-plus-{1}"
        ),
    ).row(
        telebot.types.InlineKeyboardButton(
            "Готово",
            callback_data=f"ready-parce"
        ),
    )
    bot.send_message(
        chat_id=call.from_user.id,
        text=f"Максимум необработанных заявок - {curse}",
        reply_markup=keyboard
    )
    update_positions(
        connection=create_connection(),
        order_filter=curse
    )
    return


@bot.callback_query_handler(func=lambda call: call.data.startswith("order-minus"))
def callback_inline(call: CallbackQuery):
    dispersion = int(call.data.replace("order-minus-", "")) - 1
    keyboard = telebot.types.InlineKeyboardMarkup()
    if dispersion > 0:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "-",
                callback_data=f"order-minus-{dispersion}"
            ),
            telebot.types.InlineKeyboardButton(
                "+",
                callback_data=f"order-plus-{dispersion}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "Готово",
                callback_data=f"ready-parce"
            ),
        )
    else:
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                "+",
                callback_data=f"order-plus-{dispersion}"
            ),
        ).row(
            telebot.types.InlineKeyboardButton(
                "Готово",
                callback_data=f"ready-parce"
            ),
        )
    update_positions(
        connection=create_connection(),
        order_filter=dispersion
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Максимум необработанных заявок - {dispersion}",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("order-plus"))
def callback_inline(call: CallbackQuery):
    dispersion = int(call.data.replace("order-plus-", "")) + 1
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            "-",
            callback_data=f"order-minus-{dispersion}"
        ),
        telebot.types.InlineKeyboardButton(
            "+",
            callback_data=f"order-plus-{dispersion}"
        ),
    ).row(
        telebot.types.InlineKeyboardButton(
            "Готово",
            callback_data=f"ready-parce"
        ),
    )
    update_positions(
        connection=create_connection(),
        order_filter=dispersion
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Максимум необработанных заявок - {dispersion}",
        reply_markup=keyboard
    )


while True:
    try:
        bot.polling(none_stop=True)
    except:
        continue
