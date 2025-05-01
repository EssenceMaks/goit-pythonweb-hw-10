from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import os
from dotenv import load_dotenv
import asyncio
from typing import Optional

# Загружаем переменные окружения
load_dotenv()

# Получаем URL Redis из переменных окружения или используем имя сервиса Redis для работы с Docker
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Флаг для проверки успешности подключения к Redis
redis_connected = False

async def init_limiter():
    """
    Инициализация rate limiter при запуске приложения
    """
    global redis_connected
    try:
        redis_instance = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_instance)
        redis_connected = True
        print("Rate limiter успешно инициализирован с Redis")
    except Exception as e:
        print(f"Ошибка при инициализации rate limiter: {e}")
        redis_connected = False

# Создаем зависимости для разных типов ограничения
# Ограничение: 5 запросов в минуту
rate_limit_me_endpoint = RateLimiter(times=25, seconds=60)

# Функция для создания зависимости с обработкой случая отсутствия соединения с Redis
async def check_rate_limit_me(request: Request, response: Response):
    """
    Проверяет ограничение скорости для маршрута /me
    """
    if not redis_connected:
        # Если Redis не подключен, пропускаем ограничение
        return
    
    # Используем стандартный rate limiter
    await rate_limit_me_endpoint(request, response)