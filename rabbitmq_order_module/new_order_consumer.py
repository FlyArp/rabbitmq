import pika
import json

from rabbitmq_order_module.warehouse import Warehouse


class NewOrderConsumer(object):
    """A consumer class responsible for processing new order messages from RabbitMQ.

    This consumer listens to a dedicated queue for new orders, attempts to reserve
    stock using the Warehouse module, and publishes a notification message
    based on the outcome of the stock reservation.
    """

    def __init__(self):
        """Initializes the NewOrderConsumer.

        Establishes a connection to the RabbitMQ server, declares necessary
        exchanges and a durable queue, and binds the queue to the 'new_orders_exchange'.
        Also initializes the Warehouse component for stock management.
        """

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange='new_orders_exchange', exchange_type='direct')
        self.channel.exchange_declare(exchange='notification_exchange', exchange_type='topic')
        self.channel.queue_declare(queue='new_orders_queue', durable=True)
        self.channel.queue_bind(queue='new_orders_queue', exchange='new_orders_exchange', routing_key='')

        self.warehouse = Warehouse()

    def _callback(self, ch, method, properties, body):
        """Callback function executed upon receiving a new order message.

        This function processes the order:
        1. Deserializes the JSON message body into an order dictionary.
        2. Extracts ordered items and their quantities.
        3. Attempts to reserve stock using the Warehouse.
        4. If stock is successfully reserved, acknowledges the message and publishes
           a 'processed' status notification to the 'notification_exchange'.
        5. If stock is insufficient or the message is malformed, negatively acknowledges
           the message without requeueing it.

        Args:
            ch (pika.channel.Channel): The channel object on which the message was received.
            method (pika.spec.Basic.Deliver): The delivery method frame, containing
                                              information like the delivery tag.
            properties (pika.spec.BasicProperties): The message properties, e.g., content_type.
            body (bytes): The raw message body, expected to be a JSON-encoded order.
        """
        print(" [x] Received %r" % body)

        order = json.loads(body)
        order_items = {}
        for item in order['order']:
            order_items[item['name']] = item['quantity']

        if self.warehouse.try_reserve_stock(order_items):
            ch.basic_ack(delivery_tag=method.delivery_tag)
            order['status'] = 'processed'
            self.channel.basic_publish(exchange='notification_exchange', routing_key=f'client.{order["user_id"]}.order.{order["order_id"]}', body=json.dumps(order))
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        """Starts the consumer, beginning to listen for new order messages.

        This method blocks the current thread indefinitely, waiting for messages
        to arrive at the 'new_orders_queue'.
        """
        self.channel.basic_consume(queue='new_orders_queue', on_message_callback=self._callback)
        print(' [*] Order Consumer is waiting for New Orders. To exit press Ctrl+C')
        self.channel.start_consuming()


if __name__ == '__main__':
    order_consumer = NewOrderConsumer()
    order_consumer.start_consuming()

