# app/database/models.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, BigInteger
from sqlalchemy.orm import relationship

from app.database.base.base_model import Base

from app.database.models.channel import Channel


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="bots")
    channels = relationship("Channel", back_populates="bot")
