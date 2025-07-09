import pika
import json

from rabbitmq_order_module.warehouse import Warehouse


class NewOrderConsumer(object):

    def __init__(self):

        # self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        # self.channel = self.connection.channel()
        #
        # self.channel.queue_declare(queue='new_orders_queue', durable=True)
        # self.channel.queue_bind(queue='new_orders_queue', exchange='new_orders_exchange')

        self.warehouse = Warehouse()

        print(' [*] Waiting for New Orders. To exit press Ctrl+C')


    def callback(self, ch, method, properties, body):
        print(" [x] Received %r" % body)

        order = json.loads(body)
        order_items = {}
        for item in order['items']:
            order_items[item['name']] = item['quantity']

        if self.warehouse.try_reserve_stock(order_items):
            ch.basic_ack(delivery_tag=method.delivery_tag)
            #todo send a notification
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

if __name__ == '__main__':
    new_order_consumer = NewOrderConsumer()
    order = {
        "order_id": 0,
        "user_id": 42,
        "items": [
            {"name": "laptop", "quantity": 1},
            {"name": "wireless_mouse", "quantity": 1},
            {"name": "usb_c_charger", "quantity": 3},
        ],
        "paid": 1094.95,
        # "created_at": datetime.now().isoformat(),
        "status": "new_order"
    }

    new_order_consumer.callback(None, None, None, json.dumps(order))

