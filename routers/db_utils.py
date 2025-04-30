from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect, text
from database import engine, SessionLocal
import models
from faker import Faker
import psycopg2
import os
from urllib.parse import urlparse

router = APIRouter(prefix="/db", tags=["Database Utils"])
faker = Faker()

@router.get("/status")
def db_status():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if not tables:
            return {"status": "empty", "message": "База є, але таблиць немає."}
        return {"status": "ok", "tables": tables}
    except OperationalError:
        return {"status": "fail", "message": "Немає підключення до бази даних."}

@router.post("/init")
def db_init():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if tables:
            return {"status": "exists", "message": "Таблиці вже створені."}
        models.Base.metadata.create_all(bind=engine)
        return {"status": "created", "message": "Таблиці успішно створені."}
    except OperationalError:
        raise HTTPException(status_code=500, detail="Немає підключення до бази даних.")

@router.post("/fill-fake")
def db_fill_fake(n: int = 10, request: Request = None):
    try:
        db = SessionLocal()
        inspector = inspect(engine)
        if not inspector.get_table_names():
            models.Base.metadata.create_all(bind=engine)
        from models import Contact, PhoneNumber, User
        import random
        # Определяем user_id для контактов
        user_id = None
        if request:
            user = None
            if hasattr(request, 'session'):
                user = request.session.get('user')
            if user and user.get('role') == 'superadmin':
                # Найти или создать супер-админа
                superadmin = db.query(User).filter_by(username='Super Admin').first()
                if not superadmin:
                    superadmin = User(
                        username='Super Admin',
                        email='superadmin@example.com',
                        hashed_password='not_used',
                        role='superadmin',
                        is_verified=True
                    )
                    db.add(superadmin)
                    db.commit()
                    db.refresh(superadmin)
                user_id = superadmin.id
        if not user_id:
            # Для обычного случая — взять первого пользователя
            user = db.query(User).first()
            if not user:
                user = User(
                    username='testuser',
                    email='testuser@example.com',
                    hashed_password='not_used',
                    role='user',
                    is_verified=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            user_id = user.id
        import logging
        for _ in range(n):
            first_name = faker.first_name() or "John"
            last_name = faker.last_name() or "Doe"
            email = faker.unique.email() or f"user{random.randint(1000,9999)}@example.com"
            contact = Contact(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                birthday=faker.date_of_birth(minimum_age=18, maximum_age=80),
                extra_info=faker.sentence()
            )
            db.add(contact)
            logging.info(f"Fake contact: {first_name} {last_name} {email}")
            db.flush()
            for _ in range(random.randint(1, 3)):
                import re
                raw_number = faker.phone_number()
                cleaned_number = re.sub(r'[^0-9\-+() ]', '', raw_number)
                if len(cleaned_number) < 7:
                    cleaned_number = '+380' + faker.msisdn()[:9]
                pn = PhoneNumber(
                    number=cleaned_number,
                    label=random.choice(["home", "work", "mobile"]),
                    contact_id=contact.id
                )
                db.add(pn)
        db.commit()
        return {"status": "ok", "message": f"Додано {n} випадкових контактів для user_id={user_id}."}
    except OperationalError:
        raise HTTPException(status_code=500, detail="Немає підключення до бази даних.")
    finally:
        db.close()

@router.post("/clear")
def db_clear():
    try:
        db = SessionLocal()
        from models import Contact, PhoneNumber, Avatar, Photo
        db.query(PhoneNumber).delete()
        db.query(Avatar).delete()
        db.query(Photo).delete()
        db.query(Contact).delete()
        db.commit()
        return {"status": "ok", "message": "Всі контакти видалені."}
    except OperationalError:
        raise HTTPException(status_code=500, detail="Немає підключення до бази даних.")
    finally:
        db.close()

@router.get("/check-state")
def db_check_state():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if not tables:
            return {"status": "no_tables", "message": "База існує, контактів 0 (тобто немає, створіть контакти)"}
        # Проверяем количество контактов
        db = SessionLocal()
        count = db.execute(text("SELECT COUNT(*) FROM contacts")).scalar()
        db.close()
        if count == 0:
            return {"status": "no_contacts", "message": "База існує, контактів 0 (тобто немає, створіть контакти)"}
        return {"status": "ok", "count": count}
    except OperationalError:
        return {"status": "no_db", "message": "База не існує, створіть базу"}

@router.post("/create-db")
def create_database(request: Request):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return {"status": "noenv", "message": "Для створення бази встановіть налаштування в коді за допомогою <br> env.example та перезавантажте сервер"}
    url = urlparse(db_url)
    db_name = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port or 5432
    # Перевірка на дефолтний пароль/відсутність пароля
    if not password or password == "YOUR_PASSWORD":
        return {"status": "noenv", "message": "Для створення бази встановіть налаштування в коді за допомогою <br> env.example та перезавантажте сервер"}
    try:
        conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE {db_name}")
        cur.close()
        conn.close()
        return {"status": "created", "message": f"База даних '{db_name}' створена."}
    except psycopg2.errors.DuplicateDatabase:
        return {"status": "exists", "message": f"База даних '{db_name}' вже існує."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/drop-db")
def drop_database(request: Request):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL не задан.")
    url = urlparse(db_url)
    db_name = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port or 5432
    try:
        conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cur = conn.cursor()
        # Відключити користувачів від бази
        cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}'")
        cur.execute(f"DROP DATABASE {db_name}")
        cur.close()
        conn.close()
        return {"status": "dropped", "message": f"База даних '{db_name}' видалена."}
    except psycopg2.errors.InvalidCatalogName:
        return {"status": "not_found", "message": f"База даних '{db_name}' не знайдена."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
