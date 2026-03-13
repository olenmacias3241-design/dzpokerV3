# dzpokerV3/database/__init__.py
import enum
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum, ForeignKey, Text, Numeric
from sqlalchemy.dialects.mysql import INTEGER as Integer, BIGINT as BigInteger
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
    username = Column(String(64), unique=True, nullable=True, index=True)   # 可选，钱包用户可后填
    password_hash = Column(String(255), nullable=True)                       # 可选，钱包用户可为空
    email = Column(String(255), unique=True, index=True, nullable=True)
    coins_balance = Column(Integer(unsigned=True), default=10000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    seats = relationship("TableSeat", back_populates="user")


class UserWallet(Base):
    __tablename__ = "user_wallets"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chain = Column(String(16), nullable=False)
    address = Column(String(128), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    bound_at = Column(DateTime(timezone=True), server_default=func.now())


class Club(Base):
    __tablename__ = "clubs"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer(unsigned=True), ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClubMember(Base):
    __tablename__ = "club_members"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    club_id = Column(Integer(unsigned=True), ForeignKey("clubs.id"), nullable=False)
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member", nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------- 约局（docs/requirements/13_scheduled_game_mode.md） ----------
class ScheduledGame(Base):
    __tablename__ = "scheduled_games"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    host_user_id = Column(Integer(unsigned=True), ForeignKey("users.id"), nullable=False)
    club_id = Column(Integer(unsigned=True), ForeignKey("clubs.id"), nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    start_rule = Column(String(32), default="scheduled_or_full", nullable=False)
    min_players = Column(Integer(unsigned=True), default=2, nullable=False)
    max_players = Column(Integer(unsigned=True), nullable=False)
    blinds_json = Column(String(128), nullable=False)
    buy_in_min = Column(BigInteger(unsigned=True), nullable=True)
    buy_in_max = Column(BigInteger(unsigned=True), nullable=True)
    initial_chips = Column(BigInteger(unsigned=True), nullable=True)
    password_hash = Column(String(255), nullable=True)
    invite_code = Column(String(64), unique=True, nullable=False)
    status = Column(String(32), default="Scheduled", nullable=False)
    table_id = Column(Integer(unsigned=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScheduledGamePlayer(Base):
    __tablename__ = "scheduled_game_players"
    scheduled_game_id = Column(Integer(unsigned=True), ForeignKey("scheduled_games.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    seat_order = Column(Integer(unsigned=True), default=0, nullable=False)


class GameTable(Base):
    __tablename__ = "game_tables"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    table_name = Column(String(100))
    status = Column(Enum(TableStatus), default=TableStatus.waiting)
    sb_amount = Column(Integer(unsigned=True), nullable=False)
    bb_amount = Column(Integer(unsigned=True), nullable=False)
    max_players = Column(Integer, default=9)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    club_id = Column(Integer(unsigned=True), ForeignKey("clubs.id"), nullable=True)
    scheduled_game_id = Column(Integer(unsigned=True), ForeignKey("scheduled_games.id"), nullable=True)
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


# ---------- 锦标赛（docs/requirements/12） ----------
class Tournament(Base):
    __tablename__ = "tournaments"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(16), nullable=False)
    buy_in = Column(BigInteger(unsigned=True), nullable=False)
    fee = Column(BigInteger(unsigned=True), default=0, nullable=False)
    starting_stack = Column(BigInteger(unsigned=True), nullable=False)
    max_players = Column(Integer(unsigned=True), nullable=False)
    min_players_to_start = Column(Integer(unsigned=True), default=2, nullable=False)
    blind_structure_json = Column(Text, nullable=True)
    payout_structure_json = Column(Text, nullable=True)
    status = Column(String(32), default="Registration", nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=True)
    late_reg_minutes = Column(Integer(unsigned=True), nullable=True)
    break_after_levels = Column(Integer(unsigned=True), nullable=True)
    break_duration_minutes = Column(Integer(unsigned=True), nullable=True)
    current_level_index = Column(Integer(unsigned=True), default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TournamentRegistration(Base):
    __tablename__ = "tournament_registrations"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    tournament_id = Column(Integer(unsigned=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    unregistered_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)


class TournamentBlindLevel(Base):
    __tablename__ = "tournament_blind_levels"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    tournament_id = Column(Integer(unsigned=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    level_index = Column(Integer(unsigned=True), nullable=False)
    small_blind = Column(BigInteger(unsigned=True), nullable=False)
    big_blind = Column(BigInteger(unsigned=True), nullable=False)
    ante = Column(BigInteger(unsigned=True), default=0, nullable=False)
    duration_minutes = Column(Integer(unsigned=True), nullable=False)


class TournamentPayout(Base):
    __tablename__ = "tournament_payouts"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    tournament_id = Column(Integer(unsigned=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    rank_from = Column(Integer(unsigned=True), nullable=False)
    rank_to = Column(Integer(unsigned=True), nullable=False)
    percent_value = Column(Numeric(10, 4), nullable=False)
    is_percent = Column(Boolean, default=True, nullable=False)


class TournamentTable(Base):
    __tablename__ = "tournament_tables"
    id = Column(Integer(unsigned=True), primary_key=True, index=True)
    tournament_id = Column(Integer(unsigned=True), ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    table_number = Column(Integer(unsigned=True), nullable=False)
    status = Column(String(16), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TournamentPlayer(Base):
    __tablename__ = "tournament_players"
    tournament_id = Column(Integer(unsigned=True), ForeignKey("tournaments.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    table_id = Column(Integer(unsigned=True), ForeignKey("tournament_tables.id", ondelete="SET NULL"), nullable=True)
    seat_index = Column(Integer(unsigned=True), nullable=True)
    chips = Column(BigInteger(unsigned=True), nullable=False)
    rank = Column(Integer(unsigned=True), nullable=True)
    eliminated_at = Column(DateTime(timezone=True), nullable=True)
    prize_amount = Column(BigInteger(unsigned=True), default=0, nullable=True)


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
