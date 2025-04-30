from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_, or_
from typing import List
import crud, models, schemas
from database import SessionLocal
from datetime import date, timedelta
import logging

router = APIRouter(prefix="/contacts", tags=["Contacts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi import Request

@router.post("/", response_model=schemas.Contact)
def create_contact(request: Request, contact: schemas.ContactCreate, db: Session = Depends(get_db)):
    logging.info(f"[ROUTER] create_contact RAW: {contact}")
    user = request.session.get("user")
    # Если супер-админ, разрешаем явно задавать user_id (например, для создания контактов для других пользователей)
    if user and user.get("role") == "superadmin" and contact.user_id:
        target_user_id = contact.user_id
    elif user and user.get("role") in ("user", "admin"):
        # Для обычных пользователей user_id только из сессии
        target_user_id = user.get("id")
    else:
        raise HTTPException(status_code=403, detail="Нет доступа для создания контакта")
    try:
        return crud.create_contact(db, target_user_id, contact)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

from fastapi import Request
from typing import Optional

from sqlalchemy.orm import joinedload

@router.get("/grouped", response_model=List[schemas.UserWithContacts])
def read_contacts_grouped(
    request: Request,
    db: Session = Depends(get_db),
    search: str = Query(None),
    sort: str = Query("asc")
):
    user = request.session.get("user")
    import logging
    if not user or "id" not in user or "role" not in user:
        logging.error(f"/contacts/grouped: session user is invalid: {user}")
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Определяем, кого возвращать
    query_users = db.query(models.User)
    if user["role"] == "superadmin":
        # Все пользователи
        pass
    elif user["role"] == "admin":
        # Все пользователи и админы и супер-админ
        pass
    else:
        logging.info(f"/contacts/grouped: filtering by user id {user['id']}")
        query_users = query_users.filter(models.User.id == user["id"])

    # Жадно грузим контакты
    query_users = query_users.options(joinedload(models.User.contacts))
    users = query_users.all()
    logging.info(f"/contacts/grouped: found {len(users)} users for role {user['role']}")

    # Фильтрация и сортировка контактов на уровне Python
    result = []
    for u in users:
        contacts = u.contacts
        if search:
            search_lc = search.lower()
            contacts = [c for c in contacts if search_lc in (c.first_name or '').lower() or search_lc in (c.last_name or '').lower() or search_lc in (c.email or '').lower()]
        if sort == "desc":
            contacts = sorted(contacts, key=lambda c: (c.first_name or '').lower(), reverse=True)
        else:
            contacts = sorted(contacts, key=lambda c: (c.first_name or '').lower())
        # Сериализуем ORM-объекты через pydantic
        contacts_data = [schemas.Contact.model_validate(c, from_attributes=True) for c in contacts]
        result.append(schemas.UserWithContacts(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            contacts=contacts_data
        ))
    return result

@router.get("/", response_model=List[schemas.Contact])
def read_contacts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None),
    sort: str = Query("asc"),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = request.session.get("user")
    query = db.query(models.Contact)
    # Если не указан user_id и это супер-админ — показываем все контакты
    if user_id is not None:
        query = query.filter(models.Contact.user_id == user_id)
    elif user and user.get("role") != "superadmin":
        # Обычный пользователь — только свои контакты
        query = query.filter(models.Contact.user_id == user.get("id"))
    # superadmin без user_id — все контакты
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Contact.first_name.ilike(search_pattern)) |
            (models.Contact.last_name.ilike(search_pattern)) |
            (models.Contact.email.ilike(search_pattern))
        )
    if sort == "desc":
        query = query.order_by(models.Contact.first_name.desc())
    else:
        query = query.order_by(models.Contact.first_name.asc())
    return query.offset(skip).limit(limit).all()

@router.get("/search/", response_model=List[schemas.Contact])
def search_contacts(query: str, db: Session = Depends(get_db)):
    return crud.search_contacts(db, query)

@router.get("/birthdays/", response_model=List[schemas.Contact])
def get_upcoming_birthdays(db: Session = Depends(get_db)):
    return crud.contacts_with_upcoming_birthdays(db)


def birthday_md_expr():
    return extract('month', models.Contact.birthday) * 100 + extract('day', models.Contact.birthday)

@router.get("/birthdays/next7days", response_model=List[schemas.Contact])
def get_upcoming_birthdays_next7days(db: Session = Depends(get_db)):
    today = date.today()
    in_seven_days = today + timedelta(days=7)
    today_md = today.month * 100 + today.day
    in_seven_days_md = in_seven_days.month * 100 + in_seven_days.day

    if today_md <= in_seven_days_md:
        contacts = db.query(models.Contact).filter(
            models.Contact.birthday.isnot(None),
            birthday_md_expr().between(today_md, in_seven_days_md)
        ).all()
    else:
        contacts = db.query(models.Contact).filter(
            models.Contact.birthday.isnot(None),
            or_(
                birthday_md_expr().between(today_md, 1231),
                birthday_md_expr().between(101, in_seven_days_md)
            )
        ).all()
    return contacts

@router.get("/birthdays/next12months", response_model=List[schemas.Contact])
def get_birthdays_next_12_months(db: Session = Depends(get_db)):
    today = date.today()
    today_md = today.month * 100 + today.day
    contacts = db.query(models.Contact).filter(
        models.Contact.birthday.isnot(None),
        birthday_md_expr() >= today_md
    ).order_by(
        extract('month', models.Contact.birthday),
        extract('day', models.Contact.birthday)
    ).all()
    return contacts

@router.get("/{contact_id}", response_model=schemas.Contact)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = crud.get_contact(db, contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@router.put("/{contact_id}", response_model=schemas.Contact)
def update_contact(contact_id: int, contact: schemas.ContactUpdate, db: Session = Depends(get_db)):
    logging.info(f"[ROUTER] update_contact RAW: {contact}")
    db_contact = crud.update_contact(db, contact_id, contact)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@router.delete("/{contact_id}", response_model=schemas.Contact)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = crud.delete_contact(db, contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact
