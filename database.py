from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Проверка, запущено ли приложение на Render.com
def is_render_environment():
    return os.environ.get('RENDER') == 'true' or os.environ.get('RENDER_EXTERNAL_HOSTNAME') is not None

# Проверка, запущено ли приложение в Docker
def is_docker_environment():
    # Проверяем наличие файла /.dockerenv, который есть в Docker контейнерах
    return os.path.exists("/.dockerenv")

# Получаем URL для подключения к базе данных
def get_database_url():
    # Выводим все переменные окружения для отладки
    logger.info("Все переменные окружения:")
    for key, value in os.environ.items():
        # Не выводим секретные данные полностью
        if any(secret in key.lower() for secret in ['token', 'password', 'secret', 'key']):
            logger.info(f"{key}: ***скрыто***")
        else:
            logger.info(f"{key}: {value}")

    # Если приложение запущено на Render.com
    if is_render_environment():
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("На Render.com не задана переменная окружения DATABASE_URL!")
            
            # Проверяем, есть ли база данных внутри Render.com
            if os.environ.get("RENDER_DATABASE_URL"):
                logger.info("Найдена переменная RENDER_DATABASE_URL, используем её")
                database_url = os.environ.get("RENDER_DATABASE_URL")
            else:
                logger.error("Добавьте в настройки сервиса на Render.com переменную DATABASE_URL")
                logger.error("Пример: postgresql://username:password@hostname:port/database_name")
                # В продакшене не используем резервный URL для localhost
                return None
    
    # Если приложение запущено в Docker
    elif is_docker_environment():
        # В Docker мы должны использовать имя сервиса db вместо localhost
        logger.info("Запуск в Docker контейнере")
        database_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/contacts_db")
        logger.info(f"Используется URL базы данных для Docker: {database_url}")
    else:
        # Для локальной разработки
        database_url = os.getenv("DATABASE_URL")
    
    # Второй приоритет: конструирование из отдельных параметров
    if not database_url:
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        
        # Для Docker используем имя сервиса db
        if is_docker_environment():
            db_host = os.getenv("DB_HOST", "db")
        else:
            db_host = os.getenv("DB_HOST", "localhost")
            
        db_port = os.getenv("DB_PORT", "5432")
        
        if db_name and db_user and db_password:
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Третий приоритет: значение по умолчанию (только для локальной разработки)
    if not database_url and not is_render_environment():
        if is_docker_environment():
            logger.warning("DATABASE_URL не задан в переменных окружения, используется значение по умолчанию для Docker")
            database_url = "postgresql://postgres:postgres@db:5432/contacts_db"
        else:
            logger.warning("DATABASE_URL не задан в переменных окружения, используется значение по умолчанию")
            database_url = "postgresql://postgres:postgres@localhost:5432/contacts_db"
    
    # Для совместимости с SQLAlchemy, если URL начинается с 'postgres://'
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Безопасно выводим URL без пароля для отладки
    if database_url:
        safe_url_parts = database_url.split('@')
        if len(safe_url_parts) > 1:
            credentials = safe_url_parts[0].split(':')
            if len(credentials) > 2:
                safe_url = f"{credentials[0]}:{credentials[1]}:****@{safe_url_parts[1]}"
                logger.info(f"Connecting to database: {safe_url}")
    
    return database_url

# Создаем глобальный URL для базы данных
DATABASE_URL = get_database_url()

# Проверка наличия допустимого URL для подключения к базе данных
if DATABASE_URL is None:
    logger.error("Не удалось получить URL для подключения к базе данных")
    if is_render_environment():
        logger.error("Убедитесь, что переменная DATABASE_URL задана в настройках Render.com")
        logger.error("Приложение не может работать без подключения к базе данных")
        sys.exit(1)  # Завершаем приложение с ошибкой, если нет URL для БД в продакшене

# Вывод информации об окружении
if is_render_environment():
    logger.info("Приложение запущено на платформе Render.com")
    logger.info("RENDER_EXTERNAL_HOSTNAME: " + str(os.environ.get('RENDER_EXTERNAL_HOSTNAME')))
elif is_docker_environment():
    logger.info("Приложение запущено в Docker контейнере")
else:
    logger.info("Приложение запущено в режиме локальной разработки")

# Создаем движок базы данных с подробной отладочной информацией
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,  # Важно: проверяет соединение перед использованием
    echo=(is_render_environment() or is_docker_environment())  # Включаем подробные логи SQL в продакшен режиме для отладки
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
