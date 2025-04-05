# app/database/user.py
from sqlalchemy import Column, BigInteger, Integer, DateTime, func
from sqlalchemy.orm import relationship

from app.database.base.base_model import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bots = relationship("Bot", back_populates="owner")