from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

ENV = os.getenv("APP_ENV", "local")
load_dotenv(".env.prod" if ENV == "production" else ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://julius:adminjt@localhost/postgrado")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()