import os
import random
import string
import logging
import re

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
    
    
    def __repr__(self):
        return f"<ValueUrl(id={self.id}, short_url={self.short_url}, base_url={self.base_url})>"
    
    def __str__(self):
        return f"ValueUrl(short_url={self.short_url}, base_url={self.base_url})"

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
    

class CreateCustomSlugSchema(BaseModel):
    url: str
    custom_slug: str



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
def redirect_to_short_url(short_slug: str, db: Session = Depends(get_db)):
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


def validation_custom_slug(text):
    slug = re.sub(r'\s+', '-', text.strip().lower())
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    is_valid = bool(re.match(pattern, slug))
    
    return is_valid, slug


@app.post('/custom_url_slug')
def create_custom_slug(
    payload: CreateCustomSlugSchema, db: Session = Depends(get_db)
    ) -> UrlSchema:
    
    is_valid, validate_slug = validation_custom_slug(payload.custom_slug)
    
    if not is_valid:
        logging.error(f'invalid slug format: {payload.custom_slug}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid slug format. Use only letters, numbers and hyphens (no underscores, no spaces)'
        )
        
    logging.debug('Checking DB for slug collision')
    slug_exits = db.query(ValueUrl).filter(
        ValueUrl.short_url == validate_slug
        ).first()
        
    logging.info(f'Slug exists: {slug_exits}')
        
    if slug_exits:
        logging.error('409 Conflict, slug is busy')
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='slug is alredy taken'
            )
    
    new_custom_url = ValueUrl(
        short_url=validate_slug,
        base_url=payload.url
    )
    
    db.add(new_custom_url)
    db.commit()
    db.refresh(new_custom_url)
        
    return UrlSchema(
        id=new_custom_url.id,
        short_url=new_custom_url.short_url,
        url=new_custom_url.base_url
    )



@app.get('/{custom_url_slug}')
def redirect_to_custom_url(custom_url_slug: str, db: Session = Depends(get_db)):
    custom_url_entry = db.query(ValueUrl).filter( ValueUrl.short_url == custom_url_slug).first()
    
    if not custom_url_entry:
        logging.error(f'Short custom URL: {custom_url_entry} not found')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short custom URL not found"
        )
    
    logging.debug(f'redirect {custom_url_entry} -> {custom_url_entry.base_url}')
    logging.info(f'msg: 301 ok')
    return RedirectResponse(
        url=custom_url_entry.base_url,
        status_code=status.HTTP_301_MOVED_PERMANENTLY
    )
