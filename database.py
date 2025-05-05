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
        db_host = os.getenv("DB_HOST", "postgres")  # По умолчанию 'postgres' для Docker
        db_port = os.getenv("DB_PORT", "5432")
        
        if db_name and db_user and db_password:
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Третий приоритет: значение по умолчанию
    if not database_url:
        logger.warning("DATABASE_URL не задан в переменных окружения, используется значение по умолчанию")
        database_url = "postgresql://postgres:postgres@postgres:5432/contacts_db"
    
    # Для совместимости с SQLAlchemy, если URL начинается с 'postgres://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Безопасно выводим URL без пароля для отладки
    safe_url = database_url.split('@')[0].split(':')
    if len(safe_url) >= 3:
        safe_db_url = f"{safe_url[0]}:{safe_url[1]}:****@{database_url.split('@')[1]}"
        logger.info(f"Connecting to database: {safe_db_url}")
    
    return database_url

# Создаем глобальный URL для базы данных
DATABASE_URL = get_database_url()

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True  # Важно: проверяет соединение перед использованием
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Класс для моделей SQLAlchemy
Base = declarative_base()

# Функция для получения соединения с БД в виде зависимости FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
