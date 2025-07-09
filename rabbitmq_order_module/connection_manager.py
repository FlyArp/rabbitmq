import pika
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pika.credentials import PlainCredentials
from pika import exceptions

from config import RabbitMQConfig

class ConnectionManager:

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                #todo ask Ilia if double-check needed
                if not cls._instance:
                    cls._instance = super(ConnectionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._connection = None
            self._channels = threading.local()
            self._connection_lock = threading.Lock()
            self._reconnect_executor = ThreadPoolExecutor(max_workers=1)
            self._is_connecting = False
            self._stop_reconnect = threading.Event()

            self._initialized = True
            self._connect()

    #todo ask Ilya if this method should be static
    def _get_connection_parameters(self):
        return pika.ConnectionParameters(
            host=RabbitMQConfig.HOST,
            port=RabbitMQConfig.PORT,
            credentials=PlainCredentials(RabbitMQConfig.USERNAME, RabbitMQConfig.PASSWORD),
            virtual_host=RabbitMQConfig.VIRTUAL_HOST,
            heartbeat=60
        )


    def _connect(self):
        with self._connection_lock:
            if self._connection and self._connection.is_open:
                return self._connection

            if self._is_connecting:
                print("[x] Connection in progress. Waiting...")
                return None

            self._is_connecting = True
            self._stop_reconnect.clear()

            print("[x] Attempting to connect to RabbitMQ...")
            retry_count = 0
            max_retries = 10
            retry_delay_base = 2

            while not self._stop_reconnect.is_set() and retry_count < max_retries:
                try:
                    self._connection = pika.BlockingConnection(self._get_connection_parameters())
                    print("[x] Successfully Connected to RabbitMQ.")
                    self._is_connecting = False
                    return self._connection
                except exceptions.AMQPConnectionError as e:
                    retry_count += 1
                    delay = retry_delay_base * (2 ** (retry_count - 1))
                    print(f' [!] Connection failed: {e}. Retrying in {delay:.1f}s (Attempt {retry_count} / {max_retries})...')
                    time.sleep(delay)
                except Exception as e:
                    print(f' [!] An unexpected error occurred during connection: {e}. Retrying...')
                    time.sleep(retry_delay_base)

            self._is_connecting = False
            if not self._connection or not self._connection.is_open:
                print(" [!] Failed to connect to RabbitMQ after multiple retries. System might be unrecoverable.")
                raise ConnectionError("Could not establish connection to RabbitMQ.")

    def get_channel(self):
        #todo спросить почему нельзя просто сделать not self._channels_current_channel.is_open
        if not hasattr(self._channels, 'current_channel') or \
            not self._channels.current_channel or \
            not self._channels.current_channel.is_open:

            with self._connection_lock:
                if not self._connection or not self._connection.is_open:
                    print(" [!] Connection lost. Attempting to reconnect...")
                    try:
                        self._connect()
                    except ConnectionError:
                        print(" [!] Connection could not be re-established. Cannot get channel.")
                        return None
                if self._connection and self._connection.is_open:
                    try:
                        self._channels.current_channel = self._connection.channel()
                        print(f' [x] Channel opened for thread {threading.current_thread().name}')
                    except exceptions.AMQPConnectionError as e:
                        print(f' [!] Error opening channel on existing connection: {e}. Connection might be stale.')
                        self._reconnect_async()
                        return None
                else:
                    print(' [!] Connection not established. Cannot get channel.')
                    return None
        return self._channels.current_channel

    def _reconnect_async(self):
        with self._connection_lock:
            if not self._is_connecting:
                self._reconnect_executor.submit(self._connect)

    def close_connection(self):
        with self._connection_lock:
            self._stop_reconnect.set()
            if self._connection and self._connection.is_open:
                try:
                    self._connection.close()
                    print(' [x] RabbitMQ connection closed gracefully.')
                except Exception as e:
                    print(f' [!] Error closing RabbitMQ connection: {e}')
            self._connection = None
            self._reconnect_executor.shutdown(wait=True)

## --- Example Usage (for testing purposes) ---
if __name__ == '__main__':
    def producer_task():
        manager = ConnectionManager()
        channel = manager.get_channel()
        if channel:
            try:
                ## Declare exchange and queue for testing (these would bein publisher/consumer normally)
                channel.exchange_declare(exchange='test_exchange', exchange_type='direct')
                channel.queue_declare(queue='test_queue')
                channel.queue_bind(queue='test_queue', exchange='test_exchange', routing_key='test_key')

                channel.confirm_delivery()

                for i in range(5):
                    message = f'Hello from producer {threading.current_thread().name} - {i}'
                    properties = pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
                    channel.basic_publish(
                        exchange='test_exchange',
                        routing_key='test_key',
                        body=message.encode(),
                        properties=properties
                    )
                    print(f"Sent: {message}")
                    time.sleep(1)
            except exceptions.AMQPChannelError as e:
                print(f'Producer Channel error: {e}')

            except exceptions.AMQPConnectionError as e:
                print(f'Producer Connection error: {e}')

            finally:
                pass
        else:
            print(f'Producer {threading.current_thread().name}: Could not get channel')

    def consumer_task():
        manager = ConnectionManager()
        channel = manager.get_channel()
        if channel:
            try:
                channel.queue_declare(queue='test_queue', durable=True)
                channel.basic_qos(prefetch_count=1)

                def callback(ch, method, properties, body):
                    print(f'Received by {threading.current_thread().name}: {body.decode()}')
                    time.sleep(0.5)
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                print(f'Consumer {threading.current_thread().name} starting to consume...')
                channel.basic_consume(queue='test_queue', on_message_callback=callback, auto_ack=False)
                channel.start_consuming()
            except exceptions.AMQPChannelError as e:
                print(f'Consumer Channel error: {e}. Will attempt to restart...')

            except exceptions.AMQPConnectionError as e:
                print(f'Consumer Connection error: {e}. Connection manager will handle reconnect')

            except KeyboardInterrupt:
                print(f'Consumer {threading.current_thread().name} interrupted.')

            finally:
                if channel and channel.is_open:
                    channel.stop_consuming()

    print('Starting RabbitMQ ConnectionManager Test...')

    producer_threads = [threading.Thread(target=producer_task, name=f'Producer-{i}') for i in range(2)]
    consumer_threads = [threading.Thread(target=consumer_task, name=f'Consumer-{i}') for i in range(2)]

    for t in producer_threads + consumer_threads:
        t.daemon = True
        t.start()

    try:
        print('Running for 30 seconds. Try stopping RabbitMQ briefly to test reconnect.')
        time.sleep(30)
    except KeyboardInterrupt:
        print('\nTest interrupted by user.')
    finally:
        manager_instance = ConnectionManager()
        manager_instance.close_connection()
        print('Test finished')

        