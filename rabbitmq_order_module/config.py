import os

class RabbitMQConfig:

    # --- RabbitMQ Connection Details ---
    HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    PORT = os.getenv('RABBITMQ_PORT', 5672)
    USERNAME = os.getenv('RABBITMQ_USERNAME', 'guest')
    PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')
    VIRTUAL_HOST = os.getenv('RABBITMQ_VIRTUAL_HOST', '/')

    # --- Exchange Names ---
    ## Topic exchange for general order events (new, validated, failed, etc.)
    ORDER_EVENTS_EXCHANGE = 'order_events_topic'
    # todo check how the same exchange was named in the course
    ORDER_DLX = 'order_dead_letter_exchange'
    ORDER_RETRY_EXCHANGE = 'order_retry_exchange'

    # --- Queue Names ---
    QUEUE_NEW_ORDERS = 'queue_new_orders'
    QUEUE_PROCESSING_ORDERS = 'queue_processing_orders'
    QUEUE_NOTIFICATIONS = 'queue_notifications'
    QUEUE_DEAD_LETTER = 'queue_dead_letter_orders'
    QUEUE_RETRY_1MIN = 'queue_retry_1min'
    QUEUE_RETRY_5MIN = 'queue_retry_5min'

    # --- Routing Keys ---
    ROUTING_KEY_NEW_ORDER = 'order.new'
    ROUTING_KEY_VALIDATED = 'order.validated'
    ROUTING_KEY_READY_FOR_DELIVERY = 'order.ready_for_delivery'
    ROUTING_KEY_PROCESSING_FAILED = 'order.processing.failed'
    ROUTING_KEY_CUSTOMER_NOTIFICATION = 'customer.notification'
    ROUTING_KEY_DEAD_LETTER = 'dead.letter.order'
    ROUTING_KEY_RETRY = 'retry.order'

    ## Argument for queues that should dead-letter to ORDER_DLX
    ## Used fOR QUEUE_NEW_ORDER and QUEUE_PROCESSING_ORDERS if a message fails processing
    ## todo check is the x-delivery limit correct
    ## todo check if the names are correct
    QUEUE_WITH_DLX_ARGS = {
        'x-dead-letter-exchange': ORDER_DLX,
        'x-dead-letter-routing-key': ROUTING_KEY_DEAD_LETTER,
        'x-delivery-limit': 5
    }

    ## Argument for retry queues (dead-letter back to the main order exchange), also need TTL
    RETRY_QUEUE_BASE_ARGS = {
        'x-dead-letter-exchange': ORDER_EVENTS_EXCHANGE,
        'x-dead-letter-routing-key': ROUTING_KEY_NEW_ORDER,
    }

    RETRY_QUEUE_1MIN_ARGS = {
        **RETRY_QUEUE_BASE_ARGS,
        'x-message-ttl': 60000
    }

    RETRY_QUEUE_5MIN_ARGS = {
        **RETRY_QUEUE_BASE_ARGS,
        'x-message-ttl': 300000
    }

    DEFAULT_PREFETCH_COUNT = 1