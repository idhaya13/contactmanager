# init_db.py
from database import engine, Base
from models import Contact

# This will create the SQLite database file (contacts.db) and all tables
Base.metadata.create_all(bind=engine)
print("Database and tables created.")
