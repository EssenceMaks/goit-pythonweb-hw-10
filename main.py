from fastapi import FastAPI, Request, HTTPException, Form, Depends, status, Cookie, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from datetime import timedelta
from jose import JWTError, jwt
from routers import contacts, groups, db_utils, email_verification
from database import SessionLocal, engine
from crud import get_user_by_username, update_user_role, get_user_by_id
import models
import os
from dotenv import load_dotenv
# Импортируем функции из auth.py
from auth import pwd_context, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM

load_dotenv()

# Инициализация приложения
app = FastAPI(title="Contacts API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(contacts.router, prefix="/contacts")
app.include_router(groups.router, prefix="/groups")
app.include_router(db_utils.router, prefix="/db")
# Изменяем маршрут для email_verification, убирая префикс /verify,
# чтобы /auth/register был доступен
app.include_router(email_verification.router)

# Настройка сессий
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "default_secret_key"))

# Настройка шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Функция для обработки имени пользователя для URL (удаление домена email)
def clean_username_for_url(username: str) -> str:
    if '@' in username:
        return username.split('@')[0]  # Берем только часть до @
    return username

# Функция для получения токена из cookie
async def get_token_from_cookie(access_token: Optional[str] = Cookie(None)):
    if access_token and access_token.startswith("Bearer "):
        return access_token[7:]  # Убираем "Bearer " префикс
    return None

# Обновление редиректов для использования относительных URL
@app.get("/")
async def root(request: Request):
    user = request.session.get("user")
    if user and "username" in user:
        role = user.get("role", "user")
        # Удаляем домен из email для URL
        clean_username = clean_username_for_url(user['username'])
        return RedirectResponse(url=f"/{clean_username}_{role}/", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        # Проверяем, является ли ввод email или username
        if '@' in username:
            # Поиск по email
            user = db.query(models.User).filter(models.User.email == username).first()
        else:
            # Поиск по username
            user = get_user_by_username(db, username)
        
        # Проверка для суперадмина
        if username == os.getenv("SUPERADMIN_USERNAME") and password == os.getenv("SUPERADMIN_PASSWORD"):
            # Проверяем, существует ли суперадмин в базе данных
            superadmin_user = get_user_by_username(db, username)
            
            # Генерируем уникальный ID для суперадмина если он не найден в БД
            superadmin_id = superadmin_user.id if superadmin_user else -1
            
            # Сохраняем данные суперадмина в сессии с валидным ID
            request.session["user"] = {
                "id": superadmin_id,  # Используем -1 как специальный ID для суперадмина, если нет в БД
                "username": username,
                "email": username,  # Добавляем email для суперадмина
                "role": "superadmin"
            }
            
            # Создаем JWT-токен для API-запросов суперадмина
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": username, "id": superadmin_id, "role": "superadmin", "email": username}, 
                expires_delta=access_token_expires
            )
            
            # Удаляем домен из email для URL
            clean_username = clean_username_for_url(username)
            response = RedirectResponse(url=f"/{clean_username}_superadmin/", status_code=303)
            
            # Устанавливаем cookie с токеном для суперадмина
            response.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                httponly=True,
                max_age=1800,  # 30 минут в секундах
                path="/"  # Важно - токен будет доступен для всех путей
            )
            
            return response
        
        # Проверка для обычных пользователей
        elif user and pwd_context.verify(password, user.hashed_password):
            # Проверка, подтвержден ли email
            if not user.is_verified:
                return templates.TemplateResponse("login.html", {"request": request, "error": "Пожалуйста, подтвердите ваш email перед входом"})
            
            # Сохраняем данные пользователя в сессии
            request.session["user"] = {
                "id": user.id,
                "username": user.username,
                "email": user.email,  # Добавляем email пользователя
                "role": user.role or "user"  # Используем роль из БД или по умолчанию "user"
            }
            
            # Создаем JWT-токен для API-запросов
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.username, "id": user.id, "role": user.role or "user", "email": user.email}, 
                expires_delta=access_token_expires
            )
            
            # Удаляем домен из email для URL если username это email
            clean_username = clean_username_for_url(user.username)
            response = RedirectResponse(url=f"/{clean_username}_{user.role or 'user'}/", status_code=303)
            
            # Устанавливаем cookie с токеном (исправлено)
            response.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                httponly=True,
                max_age=1800,  # 30 минут в секундах
                path="/"  # Важно - токен будет доступен для всех путей
            )
            
            return response
        else:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Неверное имя пользователя или пароль"})
    finally:
        db.close()

@app.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup", response_class=HTMLResponse)
def signup_post(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    # TODO: Зарегистрировать пользователя в БД
    request.session["user"] = {"username": username, "role": "user"}
    return RedirectResponse(f"/{username}_user/", status_code=302)

@app.get("/{username}_{role}/", response_class=HTMLResponse)
def user_dashboard(
    request: Request, 
    username: str, 
    role: str,
    token: Optional[str] = Depends(get_token_from_cookie)
):
    user = request.session.get("user")
    # Проверка на соответствие пользователя в сессии
    # Нам нужно сравнить часть до @ в сессионном имени пользователя
    if not user:
        return RedirectResponse("/login")
    
    session_clean_username = clean_username_for_url(user["username"])
    if session_clean_username != username or user["role"] != role:
        return RedirectResponse("/login")
    
    # Выводим отладочную информацию о токене в консоль
    print(f"Token from cookie: {token[:10]}..." if token else "No token")
    
    # TODO: Получить контакты только этого пользователя
    # contacts = crud.get_contacts_for_user(username)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        # "contacts": contacts,
    })

@app.get("/current_user", response_class=HTMLResponse)
def current_user(request: Request):
    # TODO: Если залогинено несколько пользователей — показать выбор
    return templates.TemplateResponse("current_user.html", {"request": request})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    response = RedirectResponse("/login")
    # Удаляем cookie с токеном
    response.delete_cookie("access_token", path="/")
    return response

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    try:
        user = get_user_by_username(db, form_data.username)
        if not user or not pwd_context.verify(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "id": user.id, "role": user.role}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()

# Эндпоинт для проверки статуса авторизации
@app.get("/auth/status")
async def auth_status(
    request: Request,
    token: Optional[str] = Depends(get_token_from_cookie)
):
    user_session = request.session.get("user")
    
    result = {
        "session_auth": bool(user_session),
        "jwt_auth": False
    }
    
    if token:
        try:
            # Проверяем валидность JWT
            jwt_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            result["jwt_auth"] = True
            result["jwt_username"] = jwt_payload.get("sub")
            result["jwt_role"] = jwt_payload.get("role", "user")
        except JWTError:
            pass
    
    return result

# Эндпоинт для изменения роли пользователя (только для админа и суперадмина)
@app.post("/users/{user_id}/change-role", response_model=dict)
async def change_user_role(
    user_id: int, 
    role_data: dict = Body(...),
    request: Request = None,
    token: Optional[str] = Depends(get_token_from_cookie)
):
    # Проверяем, авторизован ли пользователь и имеет ли права
    if not request.session.get("user") or request.session["user"].get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения роли пользователя",
        )
    
    # Получаем ID текущего пользователя из сессии
    current_user_id = request.session["user"].get("id")
    current_user_role = request.session["user"].get("role")
    
    # Проверяем, не пытается ли пользователь изменить свою собственную роль
    if str(current_user_id) == str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не можете изменить свою собственную роль",
        )
    
    # Проверяем валидность новой роли
    new_role = role_data.get("role")
    if new_role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимая роль. Допустимые значения: 'user', 'admin'",
        )
    
    # Проверяем, что пользователь не пытается изменить роль суперадмина или роль админа (если сам не суперадмин)
    db = SessionLocal()
    try:
        user_to_change = get_user_by_id(db, user_id)
        if not user_to_change:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с ID {user_id} не найден",
            )
        
        # Запрещаем менять роль суперадмина
        if user_to_change.role == "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Невозможно изменить роль суперадмина",
            )
            
        # Админ не может изменять роль других админов, только суперадмин может
        if user_to_change.role == "admin" and current_user_role != "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Админ не может менять роль других админов, только суперадмин может это делать",
            )
        
        # Обновляем роль пользователя
        updated_user = update_user_role(db, user_id, new_role)
        
        return {"status": "success", "message": f"Роль пользователя изменена на {new_role}"}
    finally:
        db.close()

# Эндпоинт для переключения между аккаунтами
@app.get("/switch_account/{user_id}", response_class=RedirectResponse)
async def switch_account(
    request: Request,
    user_id: int
):
    db = SessionLocal()
    try:
        # Получаем пользователя по ID
        user_to_switch = get_user_by_id(db, user_id)
        if not user_to_switch:
            return RedirectResponse(url="/login", status_code=303)
        
        # Сохраняем данные пользователя в сессии
        request.session["user"] = {
            "id": user_to_switch.id,
            "username": user_to_switch.username,
            "email": user_to_switch.email,
            "role": user_to_switch.role or "user"
        }
        
        # Создаем новый JWT-токен для API-запросов
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user_to_switch.username, 
                "id": user_to_switch.id, 
                "role": user_to_switch.role or "user",
                "email": user_to_switch.email
            }, 
            expires_delta=access_token_expires
        )
        
        # Удаляем домен из email для URL если username это email
        clean_username = clean_username_for_url(user_to_switch.username)
        response = RedirectResponse(url=f"/{clean_username}_{user_to_switch.role or 'user'}/", status_code=303)
        
        # Устанавливаем cookie с токеном
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800,  # 30 минут в секундах
            path="/"
        )
        
        return response
    finally:
        db.close()
