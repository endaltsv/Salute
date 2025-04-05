from sqlalchemy import Column, Integer, BigInteger, ForeignKey, DateTime, func, UniqueConstraint, Boolean

from app.database.base.base_model import Base


class ChannelMember(Base):
    __tablename__ = "channel_members"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, nullable=False)  # Новый столбец
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))

    is_available_for_broadcast = Column(Boolean, nullable=False, default=False)

    user_id = Column(BigInteger, nullable=False)

    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('bot_id', 'channel_id', 'user_id', name='uix_bot_channel_user'),
    )
