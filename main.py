from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import contacts, groups, db_utils
import models
from database import engine

# models.Base.metadata.create_all(bind=engine)  # Создание таблиц теперь только через /db/init

app = FastAPI(title="Contacts API")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(contacts.router)
app.include_router(groups.router)
app.include_router(db_utils.router)
