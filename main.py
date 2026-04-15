import os
import random
import string
import logging

from uuid import uuid4
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import Column, String

# определение логера 
logging.basicConfig(
    level=logging.DEBUG, filename='app_log.log', filemode='w',
    format="%(asctime)s %(levelname)s %(message)s"
)

# функция для работы с переменными окружения
load_dotenv()

# переменные окружения
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

# функция генерации короткой ссылки
def generate_short_url(all_chars: list[str]):
    
    logging.info('short_url_slug:')
    short_url_slug = ''
    
    for _ in range(6):
        slug = random.choice(all_chars)
        logging.info(f'slug: {slug}')
        short_url_slug += str(slug)
        logging.info(f'short_url_slug: {short_url_slug}')
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



# ручка добавления в бд короткого и длинного урла
@app.post('/short_url')
def create_short_url(
    payload: CreateUrlSchema, db: Session = Depends(get_db)
    ) -> UrlSchema:

        logging.warning('while loop')
        while True:
            short_slug = generate_short_url(all_chars)
            
            logging.debug('check db is collision')
            slug_exists = db.query(ValueUrl).filter(
                ValueUrl.short_url == short_slug
            ).first()
            logging.info(f'slug_exists: {slug_exists}')
            
            if not slug_exists:
                logging.info('msg: OK. add short slug next')
                break
                
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
        

@app.get('/{short_slug}')
def redirect_to_long_url(short_slug: str, db: Session = Depends(get_db)):
    url_entry = db.query(ValueUrl).filter( ValueUrl.short_url == short_slug).first()
    
    if not url_entry:
        logging.error(f'Short URL: {short_slug} not found')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found"
        )
    
    logging.debug(f'redirect {short_slug} -> {url_entry.base_url}')
    logging.info(f'msg: 301 ok')
    return RedirectResponse(
        url=url_entry.base_url, status_code=status.HTTP_301_MOVED_PERMANENTLY
    )
