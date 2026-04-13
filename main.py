import os
import random
import string

from uuid import uuid4
from dotenv import load_dotenv

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import Column, String


load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
SHORT_URL_LEN = int(os.getenv('SHORT_URL_LEN', '50')) 
BASE_URL_LEN = int(os.getenv('BASE_URL_LEN', '500'))

# создать движок бд
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# базовый класс таблиц
class Base(DeclarativeBase): pass

# таблица для хранения данных
class ValueUrl(Base):
    __tablename__ = 'value_url'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    short_url = Column(String(SHORT_URL_LEN))
    base_url = Column(String(BASE_URL_LEN))

# создание таблиц при запуске сервера
Base.metadata.create_all(bind=engine)
# Создание сессии бд
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# список всех символов
all_chars = list(string.ascii_letters + string.digits)


def generate_short_url(all_chars: list[str]):
    
    short_url_slug = ''
    
    for _ in range(6):
        slug = random.choice(all_chars)
        short_url_slug += str(slug)
    return short_url_slug

# зависимость бд
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


class UrlSchema(BaseModel):
    id: str
    short_url: str
    url: str


class CreateUrlSchema(BaseModel):
    url: str


@app.post('/short_url')
def create_short_url(payload: CreateUrlSchema, db: Session = Depends(get_db)) -> UrlSchema:

        short_slug = generate_short_url(all_chars)
        
        # добавление урла в таблицу бд
        new_url = ValueUrl(short_url=short_slug, base_url=payload.url)
        
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
        
        return UrlSchema(
            id=new_url.id,
            short_url=new_url.short_url,
            url=new_url.base_url
        )