import threading


class Warehouse:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self._stock = {
            "laptop": {
                "quantity": 25,
                "price": 999.99
            },
            "wireless_mouse": {
                "quantity": 100,
                "price": 19.99
            },
            "mechanical_keyboard": {
                "quantity": 50,
                "price": 89.99
            },
            "usb_c_charger": {
                "quantity": 80,
                "price": 24.99
            },
            "smartphone": {
                "quantity": 40,
                "price": 699.99
            },
            "bluetooth_headphones": {
                "quantity": 60,
                "price": 129.99
            },
            "external_hard_drive": {
                "quantity": 30,
                "price": 59.99
            },
            "webcam": {
                "quantity": 45,
                "price": 49.99
            },
            "monitor_27_inch": {
                "quantity": 20,
                "price": 219.99
            },
            "office_chair": {
                "quantity": 15,
                "price": 149.99
            }
        }
        print('Warehouse initialized')

    def get_inventory(self):
        return self._stock

    def _is_order_valid(self, order_items: dict) -> bool:

        for item, requested_qty in order_items.items():
            if item not in self._stock:
                print(f' [!] Item {item} not found in warehouse')
                return False
            if requested_qty > self._stock[item]['quantity']:
                print(f' [!] Not enough {item} in stock')
                return False

        return True

    def _remove_stock(self, order_items: dict):
        for item, qty in order_items.items():
            self._stock[item]['quantity'] -= qty
            print(f' [-] Deducted {qty} of {item}. Remaining: {self._stock[item]['quantity']}')

    def try_reserve_stock(self, order_items):
        if self._is_order_valid(order_items):
            self._remove_stock(order_items)
            return True
        return False


if __name__ == '__main__':
    warehouse = Warehouse()
    print(warehouse.get_inventory().keys())