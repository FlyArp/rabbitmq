import pika
from datetime import datetime
import json

from rabbitmq_order_module.warehouse import Warehouse


class ClientProducer(object):

    _order_id = 0
    _user_id_counter = 0

    def __init__(self):
        ClientProducer._user_id_counter += 1
        self.user_id = ClientProducer._user_id_counter
        self.warehouse = Warehouse()

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()

        if ClientProducer._order_id == 1:
            self.channel.exchange_declare(exchange='notification_exchange', exchange_type='topic')
            self.channel.exchange_declare(exchange='new_orders_exchange', exchange_type='direct')

        self.notification_queue = self.channel.queue_declare(queue='', exclusive=True, auto_delete=True)
        queue_name = self.notification_queue.method.queue
        self.channel.queue_bind(queue=queue_name, exchange='notification_exchange', routing_key=f'client.{self.user_id}.order.#')


    def collect_order(self):
        order_list = []
        available_products = self.warehouse.get_inventory()
        product_names = list(available_products.keys())

        while True:
            print('\nWhat do you want to order?')
            for i, product_name in enumerate(product_names, 1):
                print(f'- {i}. {product_name} ')
            print('- 0. Finish the order')

            try:
                choice = int(input('Enter a number: '))
                if choice == 0:
                    break
                elif 1 <= choice <= len(product_names):
                    selected_product_name = product_names[choice - 1]
                    price = available_products[selected_product_name]['price']
                    print(f'Price: {price}')

                    while True:
                        try:
                            quantity = int(input(f'How many {selected_product_name}s do you want? '))
                            if quantity > 0:
                                order_list.append({'name': selected_product_name, 'quantity': quantity})
                                break
                            else:
                                print('Quantity must be a positive number. Please try again.')
                        except ValueError:
                            print('Invalid quantity. Please enter a number.')
                else:
                    print('Invalid choice. Please enter a number from the list.')
            except ValueError:
                print('Invalid input. Please enter a number.')
            except KeyboardInterrupt:
                print('\nOrder cancelled.')
                return []

        self._send_order(order_list)




    def _send_order(self, order_list):
        ClientProducer._order_id += 1

        order = {
            "order_id": ClientProducer._order_id,
            "user_id": self.user_id,
            "order": order_list,
            "created_at": datetime.now().isoformat(),
            "status": "new_order"
        }

        body = json.dumps(order)

        self.channel.basic_publish(exchange='new_orders_exchange',
                              routing_key='',
                              body=body.encode('utf-8'),
                              properties=pika.BasicProperties(pika.delivery_mode.DeliveryMode.Persistent)
                              )

    def close_connection(self):
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
        except Exception as e:
            print(f'Error closing connection. {e}')

if __name__ == '__main__':
    client = ClientProducer()
    client.collect_order()