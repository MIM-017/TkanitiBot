import asyncio
import aiogram
import logging

NOTIFICATION_RECIPIENTS = [239363002, 792197327] #, 25428063]  # pa, me, ma
# NOTIFICATION_RECIPIENTS = [792197327]  # me


async def notify(bot: aiogram.Bot, message: str, logger: logging.Logger = None) -> None:
    """Notifies all the recipients about a certain message. Logs the exception if one occurs during sending"""

    try:
        for recipient in NOTIFICATION_RECIPIENTS:
            await bot.send_message(recipient, message)
    except Exception as e:
        logger.exception(e)


async def perpetual_status_notification(bot: aiogram.Bot, logger: logging.Logger = None, interval: int = 30) -> None:
    """Notifies all the recipients about bot's status at a set interval in minutes.
       Logs the exception if one occurs during sending"""

    while True:
        for recipient in NOTIFICATION_RECIPIENTS:
            try:
                await bot.send_message(recipient, "Статус: норма", request_timeout=30)
            except Exception as e:
                if logger:
                    logger.exception(e)

        await asyncio.sleep(60 * interval)
