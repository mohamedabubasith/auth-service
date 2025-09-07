# test_email.py
import asyncio
from app.utils.email import send_test_email

async def test_smtp():
    result = await send_test_email("abubasith456@gmail.com")
    print("Test result:", result)

if __name__ == "__main__":
    asyncio.run(test_smtp())
