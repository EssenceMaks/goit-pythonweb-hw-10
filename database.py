from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# В Render.com предоставляет переменную с URL для подключения к Postgres
# Используем внешнюю базу данных для продакшна, локальную для разработки
DATABASE_URL = os.getenv("DATABASE_URL")

# Для совместимости с SQLAlchemy, если URL начинается с 'postgres://' (как в Render),
# заменяем на 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Если DATABASE_URL не установлен, используем резервное локальное подключение
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:postgres@localhost/contacts_db"

print(f"Connecting to database: {DATABASE_URL.split('@')[0]}@****")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Добавляем функцию для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
