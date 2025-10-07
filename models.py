from sqlalchemy import Column, Integer, String, DateTime
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
