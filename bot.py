import logging
import subprocess

import telebot
from telebot.types import ReplyKeyboardRemove, CallbackQuery
from decouple import config

from bot_click import (
    RATES_URL,
    take_rates,
    take_tocken,
)
from db.init_db import insert_positions, create_connection, update_positions, get_active_records

# TELE_TOCKEN = "8094728804:AAHdXxJZ00MUlCaZaRdiRIv35yYUWtWHkJI"
print(take_rates(RATES_URL, take_tocken()))

bot = telebot.TeleBot(config("TELE_TOCKEN", cast=str))
active_process = None

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
    )
    bot.reply_to(message, "Запустить бота?", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "start-bot")
def start_bot(call: CallbackQuery):
    rates = take_rates(RATES_URL, take_tocken())
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
    if not get_active_records(connection=create_connection()):
        insert_positions(
            connection=create_connection(),
            min_summ=0,
            rate=rate,
            disperce=0,
        )
    else:
        update_positions(connection=create_connection(), rate=rate)
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
            "Запустить", 
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


@bot.callback_query_handler(func=lambda call: call.data == "start-parse")
def start_bot(call: CallbackQuery):
    global active_process
    keyboard = telebot.types.InlineKeyboardMarkup()
    record = {}
    try:
        if len(get_active_records(create_connection())) == 1:
            record = get_active_records(create_connection())[0]
        else:
            logging.error("В базе больше одной активной записи.")
        if active_process is None:
            active_process = subprocess.Popen(
                ["poetry", "run", "python", "bot_click.py", "--rate", str(record.get("disperce")), "--min_summ", str(record.get("min_summ"))],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        logging.info("Процесс запущен.")
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
    global active_process
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
    if active_process is not None:
        logging.info("Остановка процесса.")
        active_process.terminate()
        active_process = None

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
    if message.json.get("text").isdigit():
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
    bot.send_message(
        chat_id=message.from_user.id,
        text=f"Неверный формат данных, попробуй ещё раз",
        reply_markup=ReplyKeyboardRemove()
    )


while True:
    try:
        bot.polling(none_stop=True)
    except:
        continue
