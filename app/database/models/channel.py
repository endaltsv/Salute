from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base.base_model import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)

    channel_id = Column(String, nullable=False)
    channel_name = Column(String, nullable=True)

    welcome_enabled = Column(Boolean, default=True)
    welcome_message = Column(
        String,
        nullable=False,
        default="👋 Добро пожаловать в наш канал!"
    )

    has_button = Column(Boolean, default=False)
    button_type = Column(String)  # inline / reply
    button_text = Column(String, nullable=True)
    button_url = Column(String, nullable=True)

    captcha_enabled = Column(Boolean, default=False)
    captcha_text = Column(
        String,
        nullable=True,
        default="Пожалуйста, нажмите кнопку ниже, чтобы подтвердить, что вы не бот 👇"
    )
    captcha_has_button = Column(Boolean, default=False)
    captcha_button_text = Column(String, nullable=True)

    captcha_only_for_new_users = Column(Boolean, default=False)

    auto_approve_mode = Column(String, default="none")

    bot = relationship("Bot", back_populates="channels")
