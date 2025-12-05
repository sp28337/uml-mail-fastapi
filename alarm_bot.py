import asyncio
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import httpx


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


logger = logging.getLogger(__name__)
# ========== TELEGRAM CONFIG ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ========== TELEGRAM BOT POLLING TASK ==========
async def telegram_polling_task():
    """
    Фоновая задача для получения сообщений от Telegram (polling).
    Запускается в фоне при старте приложения.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.warning(
            "⚠️  TELEGRAM_BOT_TOKEN не установлен. Telegram polling отключен."
        )
        return

    logger.info("🤖 Запуск Telegram polling...")
    offset = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 30}

            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.get(url, params=params)
                data = response.json()

            if data.get("ok"):
                updates = data.get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1

                    if "message" in update:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "")

                        logger.info(f"📨 Telegram сообщение от {chat_id}: {text}")

                        # Здесь можно добавить обработку команд бота, если нужно
                        # Например, /status, /help и т.д.

        except Exception as e:
            logger.error(f"❌ Ошибка в Telegram polling: {e}")
            await asyncio.sleep(5)  # Ждем перед повторной попыткой


# ========== TELEGRAM NOTIFICATION SYSTEM ==========
async def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """
    Отправляет сообщение в Telegram.

    Параметры:
    - message: текст сообщения (может содержать HTML теги)
    - parse_mode: "HTML" или "Markdown"

    Возвращает: True если успешно, False если ошибка
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram не сконфигурирован (отсутствует TOKEN или CHAT_ID)")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)

            if response.status_code == 200:
                logger.info("✅ Сообщение в Telegram отправлено успешно")
                return True
            else:
                logger.error(
                    f"❌ Ошибка Telegram API: {response.status_code} - {response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке в Telegram: {e}")
        return False


async def notify_success(name: str, phone: str) -> None:
    """
    Отправляет уведомление об успешной отправке заявки в Telegram.
    """
    timestamp = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")

    message = f"""
<b>✅ УСПЕШНАЯ ЗАЯВКА</b>

<b>Имя:</b> {name}
<b>Телефон:</b> <code>{phone}</code>
<b>Время:</b> {timestamp}

Заявка успешно отправлена и направлена админу.
"""

    await send_telegram_message(message)


async def notify_error(
    error_type: str, error_details: str, name: str = None, phone: str = None
) -> None:
    """
    Отправляет уведомление об ошибке в Telegram.

    Параметры:
    - error_type: тип ошибки (например, "EMAIL_SEND_ERROR", "VALIDATION_ERROR", "SERVER_ERROR")
    - error_details: детальное описание ошибки
    - name, phone: опциональные данные заявки
    """
    timestamp = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")

    message = f"""
<b>⚠️ ОШИБКА СИСТЕМЫ</b>

<b>Тип:</b> {error_type}
<b>Описание:</b> <code>{error_details}</code>
<b>Время:</b> {timestamp}
"""

    if name and phone:
        message += f"""
<b>Данные заявки:</b>
• Имя: {name}
• Телефон: <code>{phone}</code>
"""

    message += "\n⚠️ <b>ТРЕБУЕТСЯ ВНИМАНИЕ!</b>"

    await send_telegram_message(message)
