from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timedelta
from database import SessionLocal
from crud import get_user_by_username
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

# Создаём контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Конфигурация JWT
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)  # Changed to auto_error=False

# Модель данных пользователя для JWT
class TokenData:
    def __init__(self, username: Optional[str] = None, user_id: Optional[int] = None):
        self.username = username
        self.user_id = user_id

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Вспомогательная функция для получения токена из разных источников
async def get_token_from_request(
    request: Request, 
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(None)
):
    # Сначала проверяем токен из OAuth2 (заголовок Authorization)
    if token:
        return token
    
    # Затем проверяем токен из Cookie
    if access_token and access_token.startswith("Bearer "):
        return access_token[7:]  # Убираем префикс "Bearer "
    
    # В крайнем случае пытаемся получить токен из заголовка вручную
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Убираем префикс "Bearer "
    
    return None

async def get_current_user(request: Request, token: Optional[str] = Depends(get_token_from_request)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Если токена нет, возвращаем ошибку авторизации
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    db = SessionLocal()
    try:
        user = get_user_by_username(db, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    finally:
        db.close()

# Вспомогательная функция для проверки прав доступа к контактам других пользователей
def check_contact_access(user, contact_user_id):
    """
    Проверяет, имеет ли пользователь доступ к контакту другого пользователя
    
    Args:
        user: Объект пользователя 
        contact_user_id: ID пользователя, которому принадлежит контакт
        
    Returns:
        bool: True если доступ разрешен, иначе False
    """
    # Супер-админ имеет доступ ко всем контактам
    if user.role == "superadmin":
        return True
    # Админ имеет доступ ко всем контактам, кроме контактов супер-админа
    elif user.role == "admin":
        # Если бы у супер-админа были контакты, здесь была бы дополнительная проверка
        return True
    # Обычный пользователь имеет доступ только к своим контактам
    else:
        return user.id == contact_user_id