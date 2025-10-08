from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    company = Column(String, default="Independent / Unknown")
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    last_contact = Column(DateTime, default=datetime.now)
    frequency = Column(Integer, default=0)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    role = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

