import logging

from decouple import config
import psycopg2


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
        """)
        connection.commit()
        logging.info("Таблица 'clicker' успешно создана.")
    except Exception as error:
        logging.error(f"Ошибка при создании таблицы: {error}")
    finally:
        cursor.close()


def insert_positions(connection, min_summ=None, rate=None, disperce=None, status=None):
    try:
        cursor = connection.cursor()
        cursor.execute(
        """
            INSERT INTO clicker (min_summ, rate, disperce) VALUES (%s, %s, %s);
        """, (min_summ, rate, disperce))
        connection.commit()
        logging.info(f"Запись с минимальной суммой '{min_summ}' успешно добавлена.")
    except Exception as error:
        logging.error(f"Ошибка при вставке данных: {error}")
    finally:
        cursor.close()


def update_positions(connection, min_summ=None, rate=None, disperce=None, status=None):
    try:
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
        cursor.close()


def get_active_records(connection):
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
        cursor.close()


if __name__ == "__main__":
    conn = create_connection()
    if conn:
        create_table(conn)
        conn.close()