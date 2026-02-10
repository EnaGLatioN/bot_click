import logging
from decouple import config
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def create_connection():
    """Создание соединения с базой данных"""
    try:
        connection = psycopg2.connect(
            dbname=config("POSTGRES_DB"),
            user=config("POSTGRES_USER"),
            password=config("POSTGRES_PASSWORD"),
            host=config("INIT_HOST"),
            port=config("INIT_PORT"),
        )
        return connection
    except Exception as error:
        logging.error(f"Ошибка подключения: {error}")
        return None


def create_table(connection):
    """Создание таблиц в базе данных"""
    try:
        cursor = connection.cursor()

        # Создаем таблицы по одной
        tables_sql = [
            """CREATE TABLE IF NOT EXISTS clicker (
                id SERIAL PRIMARY KEY,
                min_summ INT,
                rate FLOAT,
                disperce FLOAT,
                status BOOLEAN DEFAULT TRUE
            );""",
            """CREATE TABLE IF NOT EXISTS processes (
                id SERIAL PRIMARY KEY,
                command TEXT NOT NULL,
                pid INTEGER NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS lots (
                id SERIAL PRIMARY KEY,
                lot_id TEXT NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS tocken (
                id SERIAL PRIMARY KEY,
                tocken TEXT NOT NULL
            );"""
        ]

        for sql in tables_sql:
            cursor.execute(sql)

        connection.commit()
        logging.info("Все таблицы созданы.")

        # Добавляем дополнительные столбцы если нужно
        add_order_filter_column(connection)
        update_chat_column_type(connection)

    except Exception as error:
        logging.error(f"Ошибка при создании таблиц: {error}")
        if connection:
            connection.rollback()
    finally:
        if cursor:
            cursor.close()


def add_order_filter_column(connection):
    """Добавление дополнительных столбцов в таблицу clicker"""
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
        if connection:
            connection.rollback()
    finally:
        if cursor:
            cursor.close()


def update_chat_column_type(connection):
    """Обновление типа столбца chat"""
    try:
        cursor = connection.cursor()

        # Проверяем существует ли столбец chat
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='clicker' AND column_name='chat';
        """)

        if cursor.fetchone():
            # Если столбец существует, меняем тип
            cursor.execute("ALTER TABLE clicker ALTER COLUMN chat TYPE BIGINT;")
            logging.info("Тип столбца chat изменён на BIGINT.")
        else:
            # Если не существует, добавляем
            cursor.execute("ALTER TABLE clicker ADD COLUMN chat BIGINT;")
            logging.info("Столбец chat добавлен как BIGINT.")

        connection.commit()
    except Exception as error:
        logging.error(f"Ошибка при обновлении столбца chat: {error}")
        if connection:
            connection.rollback()
    finally:
        if cursor:
            cursor.close()


# ==================== ЭКСПОРТИРУЕМЫЕ ФУНКЦИИ ====================

def insert_lot(lot_id=None, status=None):
    """Вставка лота в таблицу lots"""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT 1 FROM lots WHERE lot_id = %s;", (lot_id,)
        )
        exists = cursor.fetchone()
        if exists:
            logging.info(f"Лот с лот айди '{lot_id}' уже существует. Вставка отменена.")
        else:
            cursor.execute(
                "INSERT INTO lots (lot_id, status) VALUES (%s, %s);",
                (lot_id, status)
            )
            connection.commit()
            logging.info(f"Запись с лот айди '{lot_id}' успешно добавлена.")
            return True
    except Exception as error:
        logging.error(f"Ошибка при вставке данных: {error}")
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def get_active_records(connection=None):
    """Получение активных записей из таблицы clicker"""
    cursor = None
    try:
        if connection is None:
            connection = create_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM clicker WHERE status = TRUE;")
        columns = [column[0] for column in cursor.description]
        records = [dict(zip(columns, record)) for record in cursor.fetchall()]

        for record in records:
            logging.info(f"Запись: {record}")

        return records
    except Exception as error:
        logging.error(f"Ошибка при получении данных: {error}")
        return []
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.closed == 0:
            connection.close()


# ==================== ОСТАЛЬНЫЕ ФУНКЦИИ ====================

def insert_positions(connection, min_summ=None, rate=None, disperce=None, chat=None, status=None):
    """Вставка позиций в таблицу clicker"""
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
                INSERT INTO clicker (min_summ, rate, disperce, chat) VALUES (%s, %s, %s, %s);
            """, (int(min_summ), rate, disperce, chat))
        connection.commit()
        logging.info(f"Запись с минимальной суммой '{min_summ}' успешно добавлена.")
    except Exception as error:
        logging.error(f"Ошибка при вставке данных: {error}")
    finally:
        if cursor is not None:
            cursor.close()


def insert_process(connection, process_data):
    """Вставка процесса в таблицу processes"""
    try:
        cursor = connection.cursor()
        execute_values(
            cursor,
            """
            INSERT INTO processes (command, pid) VALUES %s
            """,
            process_data
        )
        connection.commit()
        logging.info(f"{len(process_data)} записей успешно добавлено.")
    except Exception as error:
        logging.error(f"Ошибка при вставке данных: {error}")
    finally:
        if cursor is not None:
            cursor.close()


def get_token():
    """Получение токена из таблицы tocken"""
    connection = create_connection()
    token = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT tocken FROM tocken LIMIT 1
            """
        )
        result = cursor.fetchone()
        if result:
            token = result[0]
            logging.info(f"Токен получен: {token}")
        else:
            logging.warning("Токен не найден.")
    except Exception as error:
        logging.error(f"Ошибка при получении токена: {error}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return token


def get_active_processes(connection):
    """Получение активных процессов"""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM processes WHERE status = TRUE;")
        columns = [column[0] for column in cursor.description]
        records = [dict(zip(columns, record)) for record in cursor.fetchall()]
        logging.info(f"Записи: {records}")
        return records
    except Exception as error:
        logging.error(f"Ошибка при получении данных: {error}")
        return []
    finally:
        if cursor is not None:
            cursor.close()


def update_processes(connection):
    """Обновление процессов"""
    try:
        cursor = connection.cursor()
        update_query = """
            UPDATE processes 
            SET status = FALSE 
            WHERE status = TRUE;
        """
        cursor.execute(update_query)
        connection.commit()
        logging.info("Записи с статусом TRUE успешно обновлены.")
    except Exception as error:
        logging.error(f"Ошибка при обновлении данных: {error}")
    finally:
        if cursor is not None:
            cursor.close()


def update_positions(connection, min_summ=None, rate=None, disperce=None, status=None, order_filter=None, chat=None,
                     timer=None, num_proc=None):
    """Обновление позиций в таблице clicker"""
    try:
        cursor = connection.cursor()
        update_fields = []
        update_values = []
        if min_summ is not None:
            update_fields.append("min_summ = %s")
            update_values.append(int(min_summ))
        if rate is not None:
            update_fields.append("rate = %s")
            update_values.append(rate)
        if disperce is not None:
            update_fields.append("disperce = %s")
            update_values.append(disperce)
        if status is not None:
            update_fields.append("status = %s")
            update_values.append(status)
        if order_filter is not None:
            update_fields.append("order_filter = %s")
            update_values.append(order_filter)
        if chat is not None:
            update_fields.append("chat = %s")
            update_values.append(chat)
        if timer is not None:
            update_fields.append("timer = %s")
            update_values.append(timer)
        if num_proc is not None:
            update_fields.append("num_proc = %s")
            update_values.append(num_proc)
        if update_fields:
            update_query = f"""
                UPDATE clicker 
                SET {', '.join(update_fields)} 
                WHERE status = TRUE;
            """
            cursor.execute(update_query, update_values)
            connection.commit()
            logging.info("Записи с статусом TRUE успешно обновлены.")
        else:
            logging.warning("Нет данных для обновления.")
    except Exception as error:
        logging.error(f"Ошибка при обновлении данных: {error}")
    finally:
        if cursor is not None:
            cursor.close()


# ==================== ТОЧКА ВХОДА ====================

if __name__ == "__main__":
    """Основная функция для инициализации базы данных"""
    conn = create_connection()
    if conn:
        try:
            # Создаем таблицы
            create_table(conn)
            logging.info("✅ База данных успешно инициализирована.")

            # Пример использования экспортируемых функций
            # insert_lot("12345", True)
            # records = get_active_records(conn)
            # print(f"Найдено {len(records)} активных записей")

        except Exception as e:
            logging.error(f"❌ Ошибка при инициализации: {e}")
        finally:
            if conn:
                conn.close()