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

@router.post("/", response_model=schemas.Contact)
def create_contact(contact: schemas.ContactCreate, db: Session = Depends(get_db)):
    logging.info(f"[ROUTER] create_contact RAW: {contact}")
    try:
        return crud.create_contact(db, contact)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[schemas.Contact])
def read_contacts(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None),
    sort: str = Query("asc"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Contact)
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
