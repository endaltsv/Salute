import json

from app.redis_queue.connection import redis


# redis_queue/broadcast.py
async def enqueue_broadcast_task(
    bot_id: int,
    text: str,
    user_ids: list[int],
    button_text: str = None,
    button_url: str = None,
    response_chat_id: int = None,
    response_message_id: int = None,
):
    task = {
        "bot_id": bot_id,
        "text": text,
        "user_ids": user_ids,
        "button_text": button_text,
        "button_url": button_url,
        "response_chat_id": response_chat_id,
        "response_message_id": response_message_id,
    }

    queue_name = f"broadcast_tasks:{bot_id}"
    await redis.rpush(queue_name, json.dumps(task))
