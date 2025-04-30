from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from routers import contacts, groups, db_utils
from routers import email_verification
import models
from database import engine

app = FastAPI(title="Contacts API")
app.add_middleware(SessionMiddleware, secret_key="super_secret_key")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    user = request.session.get("user")
    if user:
        return RedirectResponse(f"/{user['username']}_{user['role']}/")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    import os
    from dotenv import load_dotenv
    load_dotenv()
    superadmin_username = os.getenv("SUPERADMIN_USERNAME")
    superadmin_password = os.getenv("SUPERADMIN_PASSWORD")
    if username == superadmin_username and password == superadmin_password:
        request.session["user"] = {"username": username, "role": "superadmin"}
        return RedirectResponse(f"/{username}_superadmin/", status_code=302)
    # TODO: Реализовать реальную проверку пользователя в БД
    # Пример: user = crud.get_user_by_username(username)
    # if user and verify_password(password, user.hashed_password):
    #     ...
    request.session["user"] = {"username": username, "role": "user"}
    return RedirectResponse(f"/{username}_user/", status_code=302)

@app.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup", response_class=HTMLResponse)
def signup_post(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    # TODO: Зарегистрировать пользователя в БД
    request.session["user"] = {"username": username, "role": "user"}
    return RedirectResponse(f"/{username}_user/", status_code=302)

@app.get("/{username}_{role}/", response_class=HTMLResponse)
def user_dashboard(request: Request, username: str, role: str):
    user = request.session.get("user")
    if not user or user["username"] != username or user["role"] != role:
        return RedirectResponse("/login")
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
    return RedirectResponse("/login")

app.include_router(contacts.router)
app.include_router(groups.router)
app.include_router(db_utils.router)
app.include_router(email_verification.router)
