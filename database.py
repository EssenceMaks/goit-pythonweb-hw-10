from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Получаем URL для подключения к базе данных
def get_database_url():
    # Первый приоритет: DATABASE_URL (например, от Render.com)
    database_url = os.getenv("DATABASE_URL")
    
    # Второй приоритет: конструирование из отдельных параметров
    if not database_url:
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "postgres")  # По умолчанию используем 'postgres' для Docker
        db_port = os.getenv("DB_PORT", "5432")
        
        if db_name and db_user and db_password:
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Третий приоритет: значение по умолчанию
    if not database_url:
        logger.warning("DATABASE_URL не задан в переменных окружения, используется значение по умолчанию")
        database_url = "postgresql://postgres:postgres@postgres:5432/contacts_db"
    
    # Для совместимости с SQLAlchemy, если URL начинается с 'postgres://' (как в Render), 
    # заменяем на 'postgresql://'
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Безопасно выводим URL без пароля для отладки
    safe_url = database_url.split('@')[0].split(':')[0:2]
    safe_url = ':'.join(safe_url) + ':***@' + '@'.join(database_url.split('@')[1:])
    logger.info(f"Connecting to database: {safe_url}")
    
    return database_url

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
