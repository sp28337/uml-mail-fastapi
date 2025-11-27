import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
ADMIN_MAIL = os.getenv("ADMIN_MAIL")
PORT = int(os.getenv("PORT", 3030))
CORS_FRONTEND_URL = os.getenv("CORS_FRONTEND_URL", "")
CORS_FRONTEND_URL_2 = os.getenv("CORS_FRONTEND_URL_2", "")
CORS_SECONDARY_URL = os.getenv("CORS_SECONDARY_URL", "")
CORS_SECONDARY_URL_2 = os.getenv("CORS_SECONDARY_URL_2", "")
CORS_DEV_URL = os.getenv("CORS_DEV_URL", "")

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3001",
    "http://localhost:3000",
    CORS_FRONTEND_URL,
    CORS_FRONTEND_URL_2,
    CORS_SECONDARY_URL,
    CORS_SECONDARY_URL_2,
    CORS_DEV_URL,
]


class ContactRequest(BaseModel):
    name: str
    phone: str


async def send_email(to_email: str, name: str, phone: str) -> bool:
    try:
        if SMTP_PORT == 465:
            smtp = aiosmtplib.SMTP(
                hostname=SMTP_HOST, port=SMTP_PORT, use_tls=True, timeout=10
            )
        else:
            smtp = aiosmtplib.SMTP(hostname=SMTP_HOST, port=SMTP_PORT, timeout=10)

        await smtp.connect()

        if SMTP_PORT != 465:
            await smtp.starttls()

        await smtp.login(EMAIL_USER, EMAIL_PASS)

        html = f"""
        <html>
        <body style="font-family: Arial;">
        <h2 style="color: #164e3b;">Новая заявка от клиента</h2>
        <p><strong>Имя:</strong> {name}</p>
        <p><strong>Телефон:</strong> <a href="tel:{phone}">{phone}</a></p>
        <p><strong>Время:</strong> {datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y %H:%M:%S')}</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["From"] = EMAIL_USER
        message["To"] = to_email
        message["Subject"] = f"Новая заявка от: {name}"
        message.attach(MIMEText(html, "html", "utf-8"))

        await smtp.send_message(message)
        await smtp.quit()

        logger.info(f"Письмо отправлено на {to_email}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Приложение запущено")
    yield
    logger.info("🛑 Приложение остановлено")


app = FastAPI(title="Military API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "OK"}


@app.get("/api/health")
async def health():
    return {"status": "OK"}


@app.post("/api/contact")
async def contact(request: ContactRequest):
    if not request.name or not request.phone:
        raise HTTPException(status_code=400, detail="Заполните все поля")

    if len(request.name) < 2:
        raise HTTPException(status_code=400, detail="Имя слишком короткое")

    if len(request.phone) < 10:
        raise HTTPException(status_code=400, detail="Телефон слишком короткий")

    logger.info(f"Заявка: {request.name} ({request.phone})")

    result = await send_email(ADMIN_MAIL, request.name, request.phone)

    if not result:
        raise HTTPException(status_code=500, detail="Ошибка отправки")

    return {"success": True, "message": "Заявка отправлена"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
