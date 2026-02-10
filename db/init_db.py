import logging
from decouple import config
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def create_connection():
    try:
        connection = psycopg2.connect(
            dbname=config("POSTGRES_DB"),
            user=config("POSTGRES_USER"),
            password=config("POSTGRES_PASSWORD"),
            host=config("INIT_HOST"),
            port=config("INIT_PORT"),
        )
        connection.autocommit = False  # Явно отключаем автокоммит
        return connection
    except Exception as error:
        logging.error(f"Ошибка подключения: {error}")
        return None


def create_table(connection):
    try:
        cursor = connection.cursor()

        # Сначала создаем базовые таблицы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clicker (
                id SERIAL PRIMARY KEY,
                min_summ INT,
                rate FLOAT,
                disperce FLOAT,
                status BOOLEAN DEFAULT TRUE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processes (
                id SERIAL PRIMARY KEY,
                command TEXT NOT NULL,
                pid INTEGER NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lots (
                id SERIAL PRIMARY KEY,
                lot_id TEXT NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tocken (
                id SERIAL PRIMARY KEY,
                tocken TEXT NOT NULL
            );
        """)

        connection.commit()
        logging.info("Таблицы успешно созданы.")

        # Теперь добавляем дополнительные столбцы если нужно
        add_order_filter_column(connection)
        update_chat_column_type(connection)

    except Exception as error:
        logging.error(f"Ошибка при создании таблиц: {error}")
        connection.rollback()
    finally:
        if cursor:
            cursor.close()


def add_order_filter_column(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("""
            ALTER TABLE clicker
            ADD COLUMN IF NOT EXISTS order_filter INTEGER,
            ADD COLUMN IF NOT EXISTS chat INTEGER,
            ADD COLUMN IF NOT EXISTS num_proc INTEGER,
            ADD COLUMN IF NOT EXISTS timer INTEGER;
        """)
        connection.commit()
        logging.info("Столбцы успешно добавлены в таблицу clicker.")
    except Exception as error:
        logging.error(f"Ошибка при добавлении столбцов: {error}")
        connection.rollback()
    finally:
        if cursor:
            cursor.close()


def update_chat_column_type(connection):
    try:
        cursor = connection.cursor()

        # Сначала проверяем существует ли столбец chat
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='clicker' AND column_name='chat';
        """)

        if cursor.fetchone():
            # Если столбец существует, меняем тип
            cursor.execute("""
                ALTER TABLE clicker 
                ALTER COLUMN chat TYPE BIGINT;
            """)
            logging.info("Тип столбца chat изменён на BIGINT.")
        else:
            # Если не существует, добавляем
            cursor.execute("""
                ALTER TABLE clicker 
                ADD COLUMN chat BIGINT;
            """)
            logging.info("Столбец chat добавлен как BIGINT.")

        connection.commit()
    except Exception as error:
        logging.error(f"Ошибка при обновлении столбца chat: {error}")
        connection.rollback()
    finally:
        if cursor:
            cursor.close()


# Остальные функции остаются без изменений...

if __name__ == "__main__":
    conn = create_connection()
    if conn:
        try:
            # ТОЛЬКО создаем таблицы, остальное внутри create_table
            create_table(conn)
            logging.info("База данных успешно инициализирована.")
        finally:
            if conn:
                conn.close()