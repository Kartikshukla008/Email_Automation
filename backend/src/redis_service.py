import os
import json
import redis.asyncio as redis

# Environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "emails_to_send"

redis_client = None

async def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            await redis_client.ping()
            print("Redis connected.")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            redis_client = None
    return redis_client

async def send_to_queue(data):
    r = await get_redis()
    if r:
        try:
            # Prepare message
            message = json.dumps(data)
            # Push to the list (queue)
            await r.lpush(QUEUE_NAME, message)
            print(f"Sent to Redis Queue: {data.get('email')}")
            return True
        except Exception as e:
            print(f"Redis send error: {e}")
            return False
    else:
        print("Redis not available. Skipping queue.")
        return False

    if redis_client:
        await redis_client.close()

async def set_campaign_pending(campaign_id: str, count: int):
    r = await get_redis()
    if r:
        await r.set(f"campaign:{campaign_id}:pending", count)

async def get_campaign_pending(campaign_id: str) -> int:
    r = await get_redis()
    if r:
        val = await r.get(f"campaign:{campaign_id}:pending")
        return int(val) if val else 0
    return 0

async def decrement_campaign_pending(campaign_id: str) -> int:
    r = await get_redis()
    if r:
        val = await r.decr(f"campaign:{campaign_id}:pending")
        return val
    return 0
