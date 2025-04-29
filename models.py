from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

# Association table for many-to-many Contact <-> Group
contact_group = Table(
    'contact_group', Base.metadata,
    Column('contact_id', Integer, ForeignKey('contacts.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

class Contact(Base):
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    email = Column(String, nullable=False, unique=True)
    birthday = Column(Date, nullable=False)
    extra_info = Column(Text)

    phone_numbers = relationship('PhoneNumber', back_populates='contact', cascade="all, delete-orphan")
    avatars = relationship('Avatar', back_populates='contact', cascade="all, delete-orphan")
    photos = relationship('Photo', back_populates='contact', cascade="all, delete-orphan")
    groups = relationship('Group', secondary=contact_group, back_populates='contacts')

class PhoneNumber(Base):
    __tablename__ = 'phone_numbers'
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    number = Column(String, nullable=False)
    label = Column(String, default="other")  # e.g., home, work, mobile

    contact = relationship('Contact', back_populates='phone_numbers')

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    contacts = relationship('Contact', secondary=contact_group, back_populates='groups')

class Avatar(Base):
    __tablename__ = 'avatars'
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    file_path = Column(String)  # Placeholder for future file storage
    is_main = Column(Integer, default=0)  # 1 if main, 0 otherwise
    show = Column(Integer, default=1)  # 1 if shown, 0 otherwise

    contact = relationship('Contact', back_populates='avatars')

class Photo(Base):
    __tablename__ = 'photos'
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    file_path = Column(String)
    is_main = Column(Integer, default=0)
    show = Column(Integer, default=1)

    contact = relationship('Contact', back_populates='photos')
