import pathlib
from requests import get
from json import loads
from enum import Enum
from pathlib import Path
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class _ProductCategory(Enum):
    FABRIC = 1
    FABRIC_COUPON = 2
    BUTTON = 3
    PATTERN = 4
    MISCELLANEOUS = 99


class Product:
    def __init__(self, uuid: str):
        """Initializes new product by performing a request to the API based on the provided uuid.
        Raises an exception if the request was unsuccessful"""

        product = get(f"https://api.tkaniti.ru/store/goods/u/{uuid}")

        product.raise_for_status()

        product = product.json()["data"]

        # Common fields
        self.uuid = product["uuid"]
        self.name = product["name"]
        self.description = product["description"]
        self.code = product["code"]
        self.price = product["price"]
        self.brand = product["brand"]
        self._specs = product["specs"]
        self.category = _ProductCategory(int(product["category_id"]))
        self.category_name = product["category_name"]

        if self.category == _ProductCategory.FABRIC or self.category == _ProductCategory.FABRIC_COUPON:

            if "width" in loads(self._specs):
                self.width = loads(self._specs)["width"]

            if "length" in loads(self._specs):
                self.length = loads(self._specs)["length"]

            if "composition" in loads(self._specs):
                self.composition = loads(self._specs)["composition"]

            if "density" in loads(self._specs):
                self.density = loads(self._specs)["density"]


        elif self.category_name == "Пуговка":
            self.size = loads(self._specs)["size"]
            self.color = loads(self._specs)["color"]
            self.material = loads(self._specs)["material"]

        self.images = []
        for image in product["images"]:
            self.images.append(image["filename"])

        self.videos = []
        for video in product["videos"]:
            self.videos.append(video["filename"])


    def compose_description(self) -> str:
        """Returns the description of the product, tailored to the product's category"""

        match self.category:
            case _ProductCategory.FABRIC | _ProductCategory.FABRIC_COUPON:
                price = ("Цена за метр, руб.: " if self.category == _ProductCategory.FABRIC else "Цена, руб.: ") + self.price + "\n"
                density = f"Плотность, гр/м2: {self.density}\n" if hasattr(self, "density") else ""
                length = f"Длина: {self.length}\n" if hasattr(self, "length") else ""

                desc = (f"Бренд: {self.brand}\n"
                        f"Название: {self.name}\n"
                        f"Характеристика: {self.description}\n"
                        f"{density}"
                        f"Состав: {self.composition}\n"
                        f"Ширина, см: {self.width}\n"
                        f"{length}"
                        f"{price}"
                        f"Артикул: {self.code}")

            case _:
                desc = (f"Бренд: {self.brand}\n"
                        f"Название: {self.name}\n"
                        f"Характеристика: {self.description}\n"
                        f"Артикул: {self.code}\n"
                        f"Цена, руб.: {self.price}")

        return desc


    def compose_buy_link(self) -> str:
        """Returns the link leading to the product page"""

        return f"https://tkaniti.ru/goods/{self.uuid}?utm_source=tg_channel"


    def compose_buy_keyboard(self) -> InlineKeyboardMarkup:
        """Returns a keyboard markup containing a buy button"""

        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Быстрый просмотр фото и видео", url=self.compose_buy_link()))
        builder.add(InlineKeyboardButton(text="Заказать", url=self.compose_buy_link()))
        keyboard = builder.as_markup()

        return keyboard


    def download_videos(self, path: Path):
        """Downloads the videos of the product, while assigning names in format video#"""

        for index, video in enumerate(self.videos):
            self._get_video(video, path, f"video{index}.mp4")


    def download_images(self, path: Path):
        """Downloads the images of the product, while assigning names in format photo#"""

        for index, image in enumerate(self.images):
            self._get_photo(image, path, f"photo{index}.jpg")


    def download_all_media(self, path: Path = Path("./temp")):
        """Downloads all media pertaining to the product, while assigning names in format video# or photo#"""

        self.download_videos(path)
        self.download_images(path)


    @staticmethod
    def _get_photo(file_name: str, path: Path, saved_file_name: str = "photo"):
        img = get(f"https://cdn.tkaniti.ru/store/image/{file_name}").content
        if not path.is_dir():
            path.mkdir(parents=True)
        with open(path / saved_file_name, "wb") as photo:
            photo.write(img)


    @staticmethod
    def _get_video(file_name: str, path: Path, saved_file_name: str = "video"):
        vid = get(f"https://cdn.tkaniti.ru/store/videos/{file_name}/mp4").content
        if not path.is_dir():
            path.mkdir(parents=True)
        with open(path / saved_file_name, "wb") as video:
            video.write(vid)
