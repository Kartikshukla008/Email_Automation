import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_DB = os.getenv("POSTGRES_DB", "mail_system")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DB}"

async def get_db_connection():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

async def init_db():
    conn = await get_db_connection()
    if conn:
        try:
            # Drop tables request by USER (except email_logs)
            await conn.execute("""
                DROP TABLE IF EXISTS logs CASCADE;
                DROP TABLE IF EXISTS queue_jobs CASCADE;
                DROP TABLE IF EXISTS recipients CASCADE;
                DROP TABLE IF EXISTS templates CASCADE;
                DROP TABLE IF EXISTS campaigns CASCADE;
            """)

            # Legacy table (keeping for now to avoid breaking existing code)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    status VARCHAR(50),
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Database initialized successfully.")
        finally:
            await conn.close()
    else:
        print("Could not initialize DB: No connection.")
