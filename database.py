# dzpokerV3/database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, BigInteger, Numeric
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
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=True)   # 可选，钱包用户可后填
    hashed_password = Column(String(255), nullable=True)         # 可选，钱包用户可为空；与 schema 一致
    email = Column(String(255), unique=True, nullable=True)
    nickname = Column(String(64), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    coins_balance = Column(BigInteger, default=10000, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    experience_points = Column(Integer, default=0, nullable=False)
    total_hands_played = Column(Integer, default=0, nullable=False)
    hands_won = Column(Integer, default=0, nullable=False)
    biggest_pot_won = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class UserWallet(Base):
    __tablename__ = 'user_wallets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    chain = Column(String(16), nullable=False)   # ETH|BSC|SOL|Tron
    address = Column(String(128), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    bound_at = Column(DateTime, default=datetime.utcnow)

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


# ---------- 锦标赛（docs/requirements/12_tournaments_sng_mtt.md） ----------
class Tournament(Base):
    __tablename__ = 'tournaments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    type = Column(String(16), nullable=False)  # SNG|MTT
    buy_in = Column(BigInteger, nullable=False)
    fee = Column(BigInteger, default=0, nullable=False)
    starting_stack = Column(BigInteger, nullable=False)
    max_players = Column(Integer, nullable=False)
    min_players_to_start = Column(Integer, default=2, nullable=False)
    blind_structure_json = Column(Text, nullable=True)
    payout_structure_json = Column(Text, nullable=True)
    status = Column(String(32), default='Registration', nullable=False)
    starts_at = Column(DateTime, nullable=True)
    late_reg_minutes = Column(Integer, nullable=True)
    break_after_levels = Column(Integer, default=4, nullable=True)
    break_duration_minutes = Column(Integer, default=5, nullable=True)
    current_level_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TournamentRegistration(Base):
    __tablename__ = 'tournament_registrations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    unregistered_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)


class TournamentBlindLevel(Base):
    __tablename__ = 'tournament_blind_levels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    level_index = Column(Integer, nullable=False)
    small_blind = Column(BigInteger, nullable=False)
    big_blind = Column(BigInteger, nullable=False)
    ante = Column(BigInteger, default=0, nullable=False)
    duration_minutes = Column(Integer, nullable=False)


class TournamentPayout(Base):
    __tablename__ = 'tournament_payouts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    rank_from = Column(Integer, nullable=False)
    rank_to = Column(Integer, nullable=False)
    percent_value = Column(Numeric(10, 4), nullable=False)
    is_percent = Column(Boolean, default=True, nullable=False)


class TournamentTable(Base):
    __tablename__ = 'tournament_tables'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    table_number = Column(Integer, nullable=False)
    status = Column(String(16), default='active', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TournamentPlayer(Base):
    __tablename__ = 'tournament_players'
    tournament_id = Column(Integer, ForeignKey('tournaments.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    table_id = Column(Integer, ForeignKey('tournament_tables.id', ondelete='SET NULL'), nullable=True)
    seat_index = Column(Integer, nullable=True)
    chips = Column(BigInteger, nullable=False)
    rank = Column(Integer, nullable=True)
    eliminated_at = Column(DateTime, nullable=True)
    prize_amount = Column(BigInteger, default=0, nullable=True)


# 创建所有表
Base.metadata.create_all(engine)
