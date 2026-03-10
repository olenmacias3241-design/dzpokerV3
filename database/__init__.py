# dzpokerV3/database/__init__.py
import enum
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.mysql import INTEGER as Integer
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TableStatus(enum.Enum):
    waiting = "waiting"
    playing = "playing"
    ended = "ended"

class HandStatus(enum.Enum):
    preflop = "preflop"
    flop = "flop"
    turn = "turn"
    river = "river"
    showdown = "showdown"
    ended = "ended"

class ActionType(enum.Enum):
    post_sb = "post_sb"
    post_bb = "post_bb"
    fold = "fold"
    check = "check"
    bet = "bet"
    call = "call"
    raise_ = "raise"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True)
    coins_balance = Column(Integer(unsigned=True), default=10000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    seats = relationship("TableSeat", back_populates="user")

class GameTable(Base):
    __tablename__ = "game_tables"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    table_name = Column(String(100))
    status = Column(Enum(TableStatus), default=TableStatus.waiting)
    sb_amount = Column(Integer(unsigned=True), nullable=False)
    bb_amount = Column(Integer(unsigned=True), nullable=False)
    max_players = Column(Integer, default=9)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    seats = relationship("TableSeat", back_populates="table")
    hands = relationship("Hand", back_populates="table")

class TableSeat(Base):
    __tablename__ = "table_seats"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    table_id = Column(Integer(unsigned=True), ForeignKey("game_tables.id"))
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id"))
    seat_number = Column(Integer, nullable=False)
    stack = Column(Integer(unsigned=True), nullable=False)
    is_in_hand = Column(Boolean, default=False)
    table = relationship("GameTable", back_populates="seats")
    user = relationship("User", back_populates="seats")

class Hand(Base):
    __tablename__ = "hands"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    table_id = Column(Integer(unsigned=True), ForeignKey("game_tables.id"))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    status = Column(Enum(HandStatus))
    dealer_button_position = Column(Integer)
    community_cards = Column(String(50))
    pot_size = Column(Integer(unsigned=True), default=0)
    deck_cards = Column(String(255))
    table = relationship("GameTable", back_populates="hands")
    actions = relationship("HandAction", back_populates="hand")

class HandAction(Base):
    __tablename__ = "hand_actions"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    hand_id = Column(Integer(unsigned=True), ForeignKey("hands.id"))
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id"))
    action_type = Column(Enum(ActionType), nullable=False)
    amount = Column(Integer(unsigned=True))
    action_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    hand = relationship("Hand", back_populates="actions")
    user = relationship("User")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_all_tables():
    print("Creating all database tables...")
    try:
        print("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("Tables dropped.")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"An error occurred during table creation: {e}")

if __name__ == "__main__":
    create_all_tables()
