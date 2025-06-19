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
        return connection
    except Exception as error:
        logging.error(f"Ошибка подключения: {error}")
        return None


def create_table(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clicker (
                id SERIAL PRIMARY KEY,
                min_summ INT,
                rate FLOAT,
                disperce FLOAT,
                status BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS processes (
                id SERIAL PRIMARY KEY,
                command TEXT NOT NULL,
                pid INTEGER NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS lots (
                id SERIAL PRIMARY KEY,
                lot_id TEXT NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        connection.commit()
        logging.info("Таблица clicker и processes успешно созданы.")
    except Exception as error:
        logging.error(f"Ошибка при создании таблиц: {error}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def insert_lot(connection=create_connection(), lot_id=None, status=True):
    try:
        cursor = connection.cursor()
        cursor.execute(
        """
            INSERT INTO lots (lot_id, status) VALUES (%s, %s);
        """, lot_id, status)
        connection.commit()
        logging.info(f"Запись с лот айди -- '{lot_id}' успешно добавлена.")
    except Exception as error:
        logging.error(f"Ошибка при вставке данных: {error}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def insert_positions(connection, min_summ=None, rate=None, disperce=None, chat=None, status=None):
    try:
        cursor = connection.cursor()
        cursor.execute(
        """
            INSERT INTO clicker (min_summ, rate, disperce, chat) VALUES (%s, %s, %s, %s);
        """, (min_summ, rate, disperce, chat))
        connection.commit()
        logging.info(f"Запись с минимальной суммой '{min_summ}' успешно добавлена.")
    except Exception as error:
        logging.error(f"Ошибка при вставке данных: {error}")
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def insert_process(connection, process_data):
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
        if connection is not None:
            connection.close()


def get_active_processes(connection):
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
        if connection is not None:
            connection.close()


def update_processes(connection):
    try:
        cursor = connection.cursor()
        update_query = f"""
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
        if connection is not None:
            connection.close()


def update_positions(connection, min_summ=None, rate=None, disperce=None, status=None, order_filter=None, chat=None, timer=None, num_proc=None):
    # try:
        cursor = connection.cursor()
        update_fields = []
        update_values = []
        if min_summ is not None:
            update_fields.append("min_summ = %s")
            update_values.append(min_summ)
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
    # except Exception as error:
    #     logging.error(f"Ошибка при обновлении данных: {error}")
    # finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def get_active_records(connection=create_connection()):
    try:
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
        if connection is not None:
            connection.close()


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
        logging.info("Столбец order_filter успешно добавлен в таблицу clicker.")
    except Exception as error:
        logging.error(f"Ошибка при добавлении столбца order_filter: {error}")


if __name__ == "__main__":
    conn = create_connection()
    if conn:
        add_order_filter_column(conn)
        create_table(conn)
        conn.close()