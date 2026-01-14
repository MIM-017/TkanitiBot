import logging
import aiogram

from Product import Product
from notifications import notify

def setup_module_logger(module_name, logging_level=logging.INFO) -> logging.Logger:
    """Sets up the logger for the module"""

    logger = logging.getLogger(module_name)
    logger.setLevel(logging_level)

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler("logs.txt", mode='w', encoding='utf-8')

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    formatter = logging.Formatter('{asctime} - {levelname} - {message}', style="{", datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    return logger


def log_new_product(logger: logging.Logger, product: Product = None, product_name: str | None = None):
    """Logs the message about new product, providing good info if provided"""

    if product:
        logger.info(f"Новый товар - АРТ {product.uuid} - {product.name}")
    elif product_name:
        logger.info(f"Новый товар - {product_name}")
    else:
        logger.info("Новый товар")


def log_no_new_products(logger: logging.Logger):
    """Logs the message about no new products being detected"""

    logger.info("Новых товаров не обнаружено")


def log_product_posting_canceled_sold(logger: logging.Logger, product_name, product_uuid):
    """Logs the message about product not being posted because it's already sold"""

    logger.info(f"Отмена выкладки товара, продан на сайте - АРТ {product_uuid} - {product_name}")


def log_product_posting_scheduled_not_available(logger: logging.Logger, product_name, product_uuid):
    """Logs the message about product not being posted because it's too early and the product is unavailable"""

    logger.info(f"Товара нет в продаже, не пришло время выкладки - АРТ {product_uuid} - {product_name}")


def log_product_posting_scheduled_later(logger: logging.Logger, product_name, product_uuid):
    """Logs the message about product not being posted because it's too early"""

    logger.info(f"Не пришло время выкладки товара - АРТ {product_uuid} - {product_name}")


def log_upload_command_wrong_uuid(logger: logging.Logger, product_uuid):
    """Logs the message about the upload command being called with the wrong UUID"""

    logger.info(f"Неверный вызов команды /upload - UUID {product_uuid}")


def log_upload_command_nonexistent_product(logger: logging.Logger, product_uuid):
    """Logs the message about the upload command being called, but the product not being in stock"""

    logger.info(f"Неуспешный вызов команды /upload - UUID {product_uuid} - UUID товара не обнаружен")


def log_upload_command_successful(logger: logging.Logger, product_uuid):
    """Logs the message about the upload command being called, but the product not being in stock"""

    logger.info(f"Успешный вызов команды /upload - UUID {product_uuid}")


def log_change_status(logger: logging.Logger, product_uuid):
    """Logs the message about the change of status of the product"""

    logger.info(f"Смена статуса товара - UUID {product_uuid}")


def log_post_product_description(logger: logging.Logger, product: Product = None):
    """Logs the message about product's description being posted"""

    if product:
        logger.info(f"Выкладка описания товара - UUID {product.uuid} - {product.name}")
    else:
        logger.info("Выкладка описания товара")


def log_post_product_media(logger: logging.Logger, product: Product = None):
    """Logs the message about product's media being posted"""

    if product:
        logger.info(f"Выкладка медиа товара - UUID {product.uuid} - {product.name}")
    else:
        logger.info("Выкладка медиа товара")


async def log_error(logger: logging.Logger, message: str, bot: aiogram.Bot = None) -> None:
    """Logs the error and notifies the states recipients if bot instance is provided"""

    logger.error(message)

    if bot:
        await notify(bot, message, logger)
