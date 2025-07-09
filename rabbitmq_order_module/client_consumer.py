import json

import pika



class ClientConsumer:
    _user_id_counter = 0

    def __init__(self):
        ClientConsumer._user_id_counter += 1
        self.user_id = ClientConsumer._user_id_counter

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()

        self.notification_queue = self.channel.queue_declare(queue='', exclusive=True, auto_delete=True)
        queue_name = self.notification_queue.method.queue
        self.channel.queue_bind(queue=queue_name, exchange='notification_exchange', routing_key=f'client.{self.user_id}.order.#')

    def _callback(self, ch, method, properties, body):
        order = json.loads(body)
        #todo make a enum for order statuses
        print(f'Order update status. Your order №{order["order_id"]} is {order["status"]}')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_consuming(self):
        self.channel.basic_consume(queue=self.notification_queue.method.queue, on_message_callback=self._callback)
        self.channel.start_consuming()