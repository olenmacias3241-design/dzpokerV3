# database/models.py - 新增 HandAction 模型

from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, TIMESTAMP, Index
from sqlalchemy.sql import func
from database import Base

class HandAction(Base):
    """手牌行动记录"""
    __tablename__ = "hand_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(Integer, ForeignKey("game_hands.id"), nullable=False)
    user_id = Column(String(255), nullable=False)  # 支持游客
    action_type = Column(String(20), nullable=False)  # FOLD, CHECK, CALL, BET, RAISE, ALL_IN
    amount = Column(BigInteger, nullable=True)
    stage = Column(String(20), nullable=False)  # PREFLOP, FLOP, TURN, RIVER
    action_order = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    
    __table_args__ = (
        Index('idx_hand_id', 'hand_id'),
    )
