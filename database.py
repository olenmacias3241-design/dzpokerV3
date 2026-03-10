# dzpokerV3/database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv('dzpokerV3/.env')

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'dzpoker')

DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255))
    email = Column(String(100))
    coins_balance = Column(Integer, default=10000)
    created_at = Column(DateTime, default=datetime.utcnow)

class GameTable(Base):
    __tablename__ = 'game_tables'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    small_blind = Column(Integer, default=5)
    big_blind = Column(Integer, default=10)
    max_players = Column(Integer, default=6)
    status = Column(String(20), default='waiting')
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=True)  # 新增：关联俱乐部
    created_at = Column(DateTime, default=datetime.utcnow)

class TableSeat(Base):
    __tablename__ = 'table_seats'
    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey('game_tables.id'), nullable=False)
    seat_number = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    stack = Column(Integer, default=1000)

class Hand(Base):
    __tablename__ = 'hands'
    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey('game_tables.id'), nullable=False)
    dealer_button_position = Column(Integer)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

class HandAction(Base):
    __tablename__ = 'hand_actions'
    id = Column(Integer, primary_key=True)
    hand_id = Column(Integer, ForeignKey('hands.id'), nullable=False)
    user_id = Column(String(50), nullable=False)
    action_type = Column(String(20), nullable=False)
    amount = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Club(Base):
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)

class ClubMember(Base):
    __tablename__ = 'club_members'
    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(20), default='member')
    joined_at = Column(DateTime, default=datetime.utcnow)

# 创建所有表
Base.metadata.create_all(engine)
