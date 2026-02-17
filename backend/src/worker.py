import asyncio
import os
import json
from .database import get_db_connection
from .redis_service import get_redis, QUEUE_NAME, decrement_campaign_pending

import aiosmtplib # type: ignore
from email.message import EmailMessage

# Real SMTP Email Sender
async def send_email_smtp(receiver, subject, body):
    sender_email = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not sender_email or not password:
        print("Error: SMTP_USER or SMTP_PASSWORD not set in .env")
        return False

    message = EmailMessage()
    message["From"] = sender_email
    message["To"] = receiver
    message["Subject"] = subject
    message.set_content(body)

    try:
        print(f"-------- SMTP SENDING --------")
        print(f"To: {receiver}")
        
        await aiosmtplib.send(
            message,
            hostname=smtp_server,
            port=smtp_port,
            start_tls=True,
            username=sender_email,
            password=password
        )
        
        print(f"Email sent successfully to {receiver}")
        return True
    except Exception as e:
        print(f"SMTP Error sending to {receiver}: {e}")
        return False

async def log_email_status(email, status, message):
    conn = await get_db_connection()
    if conn:
        try:
            await conn.execute(
                "INSERT INTO email_logs (email, status, message) VALUES ($1, $2, $3)",
                email, status, message
            )
        finally:
            await conn.close()

async def start_worker():
    print("Worker: Connecting to Redis...")
    redis = await get_redis()
    
    if not redis:
        print("Worker: Redis connection failed. Exiting.")
        return

    print(f"Worker: Listening on queue '{QUEUE_NAME}'...")
    
    try:
        while True:
            # brpop returns a tuple (queue_name, data) or None if timeout
            # We use a timeout to check for cancellation or keep alive, currently 0 (block forever) or 5s
            result = await redis.brpop(QUEUE_NAME, timeout=5)
            
            if result:
                _, raw_data = result
                try:
                    data = json.loads(raw_data)
                    email = data.get('email')
                    subject = data.get('subject')
                    template = data.get('template')

                    print(f"Worker: Processing {email}")
                    
                    # Send Email
                    try:
                        success = await send_email_smtp(email, subject, template)
                        if success:
                            await log_email_status(email, 'SENT', 'Email sent successfully via SMTP')
                        else:
                            await log_email_status(email, 'FAILED', 'SMTP Transmission Failed')
                    except Exception as e:
                        print(f"Worker: Failed to send to {email}: {e}")
                        try:
                            await log_email_status(email, 'FAILED', str(e))
                        except Exception:
                            pass # Database logging failed, prevent crash
                    
                    cid = data.get('campaign_id')
                    if cid:
                        try:
                            remaining = await decrement_campaign_pending(cid)
                            print(f"Worker: Campaign {cid} remaining: {remaining}")
                        except Exception as e:
                            print(f"Worker: Failed to update pending count for {cid}: {e}")
                            
                except json.JSONDecodeError:
                    print(f"Worker: Failed to decode message: {raw_data}")
                except Exception as e:
                    print(f"Worker: Unexpected error processing message: {e}")
            else:
                # No message in queue, just loop
                # print("Worker: Waiting for messages...")
                await asyncio.sleep(0.1) # Yield control
                
    except asyncio.CancelledError:
        print("Worker: Cancelled")
    except Exception as e:
        print(f"Worker process error: {e}")

if __name__ == "__main__":
    asyncio.run(start_worker())
