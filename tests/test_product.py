import unittest, json

from unittest import mock

from Product import Product, _ProductCategory

class TestProduct(unittest.TestCase):

    @staticmethod
    def mocked_requests_get(url):
        class MockResponse:
            def __init__(self, url):
                if url == "https://api.tkaniti.ru/store/goods/u/E7ECC50D":
                    with open("test_jsons/button_json", "r") as f:
                        self.data = f.readline()
                elif url == "https://api.tkaniti.ru/store/goods/u/7FC0E695":
                    with open("test_jsons/fabric_json", "r") as f:
                        self.data = f.readline()
                elif url == "https://api.tkaniti.ru/store/goods/u/34414165":
                    with open("test_jsons/miscellaneous_json", "r") as f:
                        self.data = f.readline()

                self.data = json.loads(self.data)


            def raise_for_status(self):
                pass


            def json(self):
                return self.data


        return MockResponse(url)

    @mock.patch('Product.get', side_effect=mocked_requests_get)
    def test_product_instantiation_yields_correct_general_fields(self, mock_get):

        fabric = Product("7FC0E695")

        self.assertEqual(fabric.uuid, "7FC0E695")
        self.assertEqual(fabric.name, "Джинс двусторонний")
        self.assertEqual(fabric.description, "Серия \"summer time\", двусторонний смесовый джинс. Пластичный, шелковистый, пружинит, великолепный.")
        self.assertEqual(fabric.code, "6543")
        self.assertEqual(fabric.price, "2700.00")
        self.assertEqual(fabric.brand, "LORO PIANA")
        self.assertEqual(fabric._specs, "{\"width\": \"152\", \"composition\": \"48% хлопок/52% шерсть\"}")
        self.assertEqual(fabric.category, _ProductCategory(1))
        self.assertEqual(fabric.category_name, "Ткань")


    @mock.patch('Product.get', side_effect=mocked_requests_get)
    def test_product_instantiation_yields_correct_fabric_fields(self, mock_get):

        fabric = Product("7FC0E695")

        self.assertEqual(fabric.width, "152")
        self.assertEqual(fabric.composition, "48% хлопок/52% шерсть")


    @mock.patch('Product.get', side_effect=mocked_requests_get)
    def test_product_instantiation_yields_correct_button_fields(self, mock_get):

        button = Product("E7ECC50D")

        self.assertEqual(button.size, "28")
        self.assertEqual(button.color, "Золото")
        self.assertEqual(button.material, "Металл")


    @mock.patch('Product.get', side_effect=mocked_requests_get)
    def test_product_compose_buy_link_composes_correct_link(self, mock_get):

        fabric = Product("7FC0E695")

        self.assertEqual(fabric.compose_buy_link(), "https://tkaniti.ru/goods/7FC0E695")


if __name__ == '__main__':
    unittest.main()
