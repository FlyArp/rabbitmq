import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

# --- New Orders ---
channel.exchange_declare(exchange='new_orders_exchange', exchange_type='direct')
channel.queue_declare(queue='new_orders_queue', durable=True)
channel.queue_bind(queue='new_orders_queue', exchange='new_orders_exchange')

# --- Process Orders ---
channel.exchange_declare(exchange='process_orders_exchange', exchange_type='direct')
channel.queue_declare(queue='process_orders_queue', durable=True)
channel.queue_bind(queue='process_orders_queue', exchange='process_orders_exchange')

# --- Notifications ---
# channel.queue_declare(queue='notifications_queue', durable=True)
channel.exchange_declare(exchange='notifications_exchange', exchange_type='topic')
# channel.queue_bind(queue='notifications_queue', exchange='process_orders_exchange')


