import requests
import time
import asyncio

from json import loads
from typing import Literal
from pprint import pp
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramEntityTooLarge, TelegramRetryAfter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.enums import ParseMode
from aiogram.filters.command import Command, CommandObject

from logs import *
from Product import Product
from notifications import perpetual_status_notification
from config import *

logger = setup_module_logger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher()

products_to_post = []


@dp.message(Command("upload"))
async def upload(msg: types.Message, command: CommandObject):
    if command.args is None:
        await msg.reply("Не указан артикул товара для загрузки. \n"
                        "Пришлите команду в формате /upload <UUID ТОВАРА>, "
                        "например  /upload 044A38E5", parse_mode=ParseMode.MARKDOWN)

        log_upload_command_wrong_uuid(logger, msg.text)  # Logging

    elif not requests.get(f"https://api.tkaniti.ru/store/goods/u/{command.args}").ok:
        await msg.answer("UUID товара не обнаружен, возможно товар уже продан")

        log_upload_command_nonexistent_product(logger, command.args)  # Logging

    else:
        uuid = command.args
        if check_post(uuid):
            keyboard_builder = InlineKeyboardBuilder()
            keyboard_builder.add(types.InlineKeyboardButton(text="Всё равно выложить", callback_data="post" + uuid))
            keyboard_builder.add(types.InlineKeyboardButton(text="Отмена", callback_data="cancel"))

            await msg.answer("Согласно базе данных, товар с данным артикулом уже был выложен",
                             reply_markup=keyboard_builder.as_markup())
        else:
            product = Product(command.args)
            await post_product(product, chat_id=POST_TO_ID, force_post=True)

        log_upload_command_successful(logger, command.args)  # Logging


@dp.callback_query()
async def force_upload(callback: types.CallbackQuery):
    """Callback handler for cases when the product is already posted."""

    message_id = callback.message.message_id
    chat_id = callback.message.chat.id

    if callback.data.startswith("post"):

        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Выкладываю...", reply_markup=None)

        try:
            product = Product(callback.data[4:])
        except Exception:
            await callback.message.answer("Произошла непредвиденная ошибка!")
            return

        await post_product(product, chat_id=POST_TO_ID, force_post=True)
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Товар выложен", reply_markup=None)

    else:

        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)


def compose(uuid: str, status: Literal["new", "restock", "sold"] = "new") -> str:
    if status == "sold":
        return "📍Закончился📍"
    else:
        product = Product(uuid)
        return product.compose_description()


def check_post(uuid: str) -> bool:
    """
    Checks whether the product was already posted

    :arg uuid: uuid of the product to check
    :return: True if the product was already posted, otherwise returns False
    """

    with open("posted.txt", "r") as posted:
        data = posted.read()

    if uuid in data:
        return True
    else:
        return False


def check_status(uuid: str) -> Literal["sold", "in_stock", "not_posted"]:
    with open("posted.txt", "r") as posted:
        _ = posted.read().split("\n")
    for entry in _:
        if uuid in entry:
            status = entry.split(":")[2]
            break

    if "status" not in locals():
        return "not_posted"

    if status == "AVL":
        return "in_stock"
    elif status == "UNAVL":
        return "sold"


def add_entry(uuid: str):
    with open("posted.txt", "a") as posted:
        posted.write(f"{uuid}:NONE:AVL\n")


async def change_status(uuid: str, mark_as_sold: bool = False):
    new_text = compose(uuid, status="sold" if mark_as_sold else "restock")

    with open("posted.txt", "r") as posted:
        data = posted.readlines()

        for index, line in enumerate(data):
            entry_uuid, message_id, status = line.split(":")

            if entry_uuid == uuid:
                break

        match status[:-1]:
            case "AVL":
                print(status[:-1])
                if mark_as_sold:
                    status = "UNAVL\n"

            case "UNAVL":
                print(status[:-1])
                if not mark_as_sold:
                    status = "AVL\n"

        new_entry = f"{entry_uuid}:{message_id}:{status}"
        data[index] = new_entry

    with open("posted.txt", "w") as posted:
        posted.write("".join(data))

    if message_id == "NONE":
        print("Игнорирую продукт до запуска")
        return

    if not mark_as_sold:
        keyboard = Product(uuid).compose_buy_keyboard()
    else:
        keyboard = None

    print("ЛОГИРОВАНИЕ: СМЕНА ТЕКСТА", uuid, new_text, message_id)
    await bot.edit_message_text(text=new_text,
                                chat_id=POST_TO_ID,
                                message_id=int(message_id),
                                reply_markup=keyboard,
                                request_timeout=60)

    log_change_status(logger, uuid)  # Logging


def post(text: str, chat_id: str = "792197327", mode: str = "t", image_name: str = "single_photo",
         video_name: str = "video",
         media_group=None):
    async def _():
        if mode == "t":
            await bot.send_message(chat_id=chat_id, text=text)

        elif mode == "p":
            img = types.FSInputFile(f"temp/{image_name}")
            await bot.send_photo(chat_id=chat_id, photo=img, caption=text)

        elif mode == "pv" or mode == "vp":
            img = types.FSInputFile(f"temp/{image_name}")
            vid = types.FSInputFile(f"temp/{video_name}")
            await bot.send_video(chat_id=chat_id, video=vid)
            await bot.send_photo(chat_id=chat_id, photo=img, caption=text)

        elif mode == "mg":
            post_id = await bot.send_media_group(chat_id=chat_id, media=media_group.build())
            post_id = post_id[0].message_id

            return post_id

    return _()


async def post_product_description(product: Product, chat_id: str = "792197327", include_buy_button: bool = True):
    """Posts the description provided by the product. Optionally adds a buy button to the description. Returns post id"""

    keyboard = None
    if include_buy_button:
        keyboard = product.compose_buy_keyboard()

    post_id = await bot.send_message(chat_id=chat_id,
                                     text=product.compose_description(),
                                     reply_markup=keyboard,
                                     request_timeout=150)
    post_id = post_id.message_id

    log_post_product_description(logger, product)  # Logging

    return post_id


async def post_product_media(product: Product, chat_id: str = "792197327"):
    """Posts all the media belonging to a product, but not more than the limit"""

    media_group = MediaGroupBuilder()

    product.download_all_media(Path("./temp"))

    count = 0
    for index in range(len(product.images)):
        if count == 10:
            break
        media_group.add_photo(types.FSInputFile(f"temp/photo{index}.jpg"))
        count += 1

    for index in range(len(product.videos)):
        if count == 10:
            break
        media_group.add_video(types.FSInputFile(f"temp/video{index}.mp4"))


    await bot.send_media_group(chat_id=chat_id, media=media_group.build(), request_timeout=150)

    log_post_product_media(logger, product)  # Logging


async def post_product(product: Product, chat_id: str = "792197327", force_post: bool = False):
    """Posts product's description and media. If the product is new, writes an entry"""

    try:
        if not check_post(product.uuid) or force_post:
            await post_product_media(product, chat_id)
            post_id = await post_product_description(product, chat_id)

            if not check_post(product.uuid):
                with open("posted.txt", "a") as posted:
                    posted.write(f"{product.uuid}:{post_id}:{'AVL'}\n")

    except TelegramEntityTooLarge as exception:
        await log_error(logger, "Получена ошибка 'Слишком большой файл' при попытке отправки поста."
                                f" Выкладка невозможнa. UUID - {product.uuid}", bot)


def create_posted_file():
    """Checks if posted file is present, if not, creates one"""

    posted_path = Path("posted.txt")
    if not posted_path.is_file():
        posted_path.touch()


async def main():
    create_posted_file()

    previous_goods = requests.get("https://api.tkaniti.ru/store/goods").json()["data"]

    for product in previous_goods:
        uuid = product["uuid"]
        if not check_post(uuid):
            add_entry(uuid)

    while True:

        # Try/except to avoid crashes caused by all kinds of connectivity issues
        try:
            response = requests.get("https://api.tkaniti.ru/store/goods")
        except requests.exceptions.ConnectionError as e:
            logger.exception(e)
            continue
        except Exception as e:
            logger.exception(e)
            continue

        # Checking if our response is okay to avoid exceptions caused by trying to get non-existent keys
        if not response.ok:
            await asyncio.sleep(5)
            continue
        else:
            current_goods = response.json()["data"]

        current_time = time.time()
        next_post_time = current_time + 0.25 * 60 * 60

        new = False
        for good in current_goods:

            status = check_status(good["uuid"])
            if status == "not_posted" and good not in [_[1] for _ in products_to_post]:
                new = True
                print("NEW GOOD DETECTED", good["name"], time.strftime("%H:%M:%S", time.localtime()))

                log_new_product(logger, product_name=good["name"])  # Logging

                if good not in [_[1] for _ in products_to_post]:
                    products_to_post.append([next_post_time, good])
            elif status == "sold":  # If the good was marked as sold but appeared again, mark it available

                try:
                    await change_status(good["uuid"])
                except Exception as e:
                    print(e)
                    await log_error(logger, f"Произошла ошибка при попытке смены статуса. UUID - {good['uuid']}", bot)

        if not new:
            print("NOTHING HERE", time.strftime("%H:%M:%S", time.localtime()))

            log_no_new_products(logger)  # Logging

        posted_products = []
        for product in products_to_post:
            if product[0] <= current_time:
                if product[1] in current_goods:
                    try:
                        await post_product(Product(product[1]["uuid"]), POST_TO_ID)
                        posted_products.append(product)
                    except Exception as e:
                        await log_error(logger, f"Произошла ошибка при выкладке товара. UUID - {product[1]['uuid']}", bot)
                else:
                    print(product[1]["name"], product[1]["uuid"], "продан на сайте, не выкладываю")
                    posted_products.append(product)

                    log_product_posting_canceled_sold(logger, product[1]["name"], product[1]["uuid"])  # Logging

            elif product[1] not in current_goods:
                print(product[1]["name"], product[1]["uuid"], "отсутствует в продаже, не выкладываю")

                log_product_posting_scheduled_not_available(logger, product[1]["name"], product[1]["uuid"])  # Logging

            elif product[0] >= current_time:
                print(product[1]["name"], "Не пришло время выкладки",
                      time.strftime("%H:%M:%S", time.localtime(product[0])))

                log_product_posting_scheduled_later(logger, product[1]["name"], product[1]["uuid"])  # Logging

        for product in posted_products:
            products_to_post.remove(product)

        for product in previous_goods:
            if product not in current_goods and check_post(product["uuid"]):
                try:
                    await change_status(product["uuid"], mark_as_sold=True)
                except TelegramBadRequest as e:
                    await post(str(e))
                    await post(str(product))
                except TimeoutError as e:
                    await log_error(logger,
                                    f"Произошла ошибка таймаута при попытке смены статуса. UUID - {product['uuid']}.",
                                    bot)
                except TelegramRetryAfter:
                    await log_error(logger, f"Произошла ошибка превышения по количеству запросов. UUID - {product['uuid']}.", # TODO: Почистить вывод
                                    bot)

        previous_goods = current_goods.copy()

        await asyncio.sleep(60)


async def run():
    await asyncio.gather(main(),
                         dp.start_polling(bot, polling_timeout=30),
                         perpetual_status_notification(bot, logger))  # Increased timeout to 30


if __name__ == "__main__":
    asyncio.run(run())
    pass

# This is the old post_product method

# async def post_product(product, chat_id: str, force_post: int = 0):
#     uuid = product["uuid"]
#     product = requests.get(f"https://api.tkaniti.ru/store/goods/u/{uuid}").json()["data"]
#     msg = compose(uuid)
#     pp(product)
#     if "image" in product.keys():
#         img = product["image"]
#         get_photo(img, saved_file_name="single_photo")
#     else:
#         imgs = [product["images"][x]["filename"] for x in range(len(product["images"]))]
#         for x in range(len(product["images"])):
#             get_photo(file_name=imgs[x], saved_file_name=f"photo{x}")
#
#     if "videos" in product.keys() and len(product["videos"]) > 0:
#         vid = product["videos"][0]["filename"]
#         get_video(vid)
#
#
#     if not check_post(uuid) or force_post:
#         media_group = MediaGroupBuilder(caption=msg)
#
#         if "videos" in product.keys() and len(product["videos"]) > 0:
#             media_group.add_video(types.FSInputFile(f"temp/video"))
#
#         if "image" in product.keys():
#             media_group.add_photo(types.FSInputFile("temp/single_photo"))
#             post_id = await post(text=msg, chat_id=chat_id, mode="mg", media_group=media_group)
#         else:
#             for x in range(min(9, len(product["images"]))):
#                 media_group.add_photo(types.FSInputFile(f"temp/photo{x}"))
#             post_id = await post(text=msg, chat_id=chat_id, mode="mg", media_group=media_group)
#
#         if not check_post(uuid):
#             with open("posted.txt", "a") as posted:
#                 posted.write(f"{uuid}:{post_id}:{'AVL'}\n")
#                 # posted.write(uuid + ":" + str(post_id) + "\n")

# Tkaniti id -1001741435947
# MY ID 792197327
