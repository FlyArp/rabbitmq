import json

import pika


class ClientConsumer:
    """A consumer class for receiving order notifications from RabbitMQ.

    This consumer connects to RabbitMQ, declares a topic exchange for notifications,
    and creates an exclusive, auto-deleting queue to receive updates specifically
    for orders placed by this client instance.
    """
    _user_id_counter = 0

    def __init__(self):
        """Initializes the ClientConsumer, establishes a connection to RabbitMQ,
        and sets up the necessary exchange and queue for notifications.
        """
        ClientConsumer._user_id_counter += 1
        self.user_id = ClientConsumer._user_id_counter

        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange='notification_exchange', exchange_type='topic')
        self.notification_queue = self.channel.queue_declare(queue='', exclusive=True, auto_delete=True)
        queue_name = self.notification_queue.method.queue
        self.channel.queue_bind(queue=queue_name, exchange='notification_exchange',
                                routing_key=f'client.{self.user_id}.order.#')

    def _callback(self, ch, method, properties, body):
        """Callback function executed when a notification message is received.

        Parses the incoming JSON message and prints the order's status update.
        Acknowledges the message upon successful processing.

        Args:
            ch (pika.channel.Channel): The channel object.
            method (pika.spec.Basic.Deliver): The delivery method frame.
            properties (pika.spec.BasicProperties): The message properties.
            body (bytes): The body of the message, expected to be JSON-encoded order status.
        """
        order = json.loads(body)
        print(f'Order update status. Your order №{order["order_id"]} is {order["status"]}')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_consuming(self):
        """Starts the consumer, blocking indefinitely to listen for messages.

        This method will block the current thread, continuously waiting for
        messages to arrive at the bound notification queue.
        """
        self.channel.basic_consume(queue=self.notification_queue.method.queue, on_message_callback=self._callback)
        self.channel.start_consuming()


if __name__ == '__main__':
    client = ClientConsumer()
    print(' [*] Client Consumer is waiting for New Orders. To exit press Ctrl+C')
    client.start_consuming()
