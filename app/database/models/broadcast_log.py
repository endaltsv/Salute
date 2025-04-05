from sqlalchemy import Column, Integer, BigInteger, Text, DateTime, func, Boolean, JSON
from app.database.base.base_model import Base


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, nullable=False)
    total_users = Column(Integer, nullable=False)
    successful = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message_text = Column(Text, nullable=False)
    button_text = Column(Text)
    button_url = Column(Text)

    progress_chat_id = Column(BigInteger)
    progress_message_id = Column(BigInteger)

    completed = Column(Boolean, default=False)
