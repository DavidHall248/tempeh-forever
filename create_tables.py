import psycopg2
from psycopg2 import sql

conn_str = "postgresql://<CONNECTION STRING HERE>"


try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    create_events_table = """
    DROP TABLE IF EXISTS events;
    CREATE TABLE IF NOT EXISTS events (
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        category VARCHAR(64),
        value INTEGER

    );
    """
    
    create_measurements_table = """
    DROP TABLE IF EXISTS measurements;
    CREATE TABLE IF NOT EXISTS measurements (
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        category VARCHAR(64),
        value DECIMAL(5,2)
    );
    """

    cur.execute(create_events_table)
    cur.execute(create_measurements_table)

    conn.commit()

except Exception as e:
    print(f"Error: {e}")

finally:
    if conn:
        cur.close()

        conn.close()
