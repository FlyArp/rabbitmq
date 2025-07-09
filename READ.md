# RabbitMQ Order Processing System

A simple demonstration of a distributed order processing system using RabbitMQ. This project simulates clients placing orders, a warehouse managing stock, and a system for sending and receiving order status notifications.

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
- [How to Run](#how-to-run)
- [System Flow](#system-flow)
- [RabbitMQ Components](#rabbitmq-components)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

## Features
- **Order Creation:** Clients can interactively select products and quantities to place new orders.
- **Stock Reservation:** A warehouse component attempts to reserve stock for incoming orders.
- **Asynchronous Processing:** Uses RabbitMQ to decouple order placement from stock processing.
- **Order Status Notifications:** Sends and receives real-time notifications about order processing outcomes (e.g., 'processed' status).
- **Persistent Messaging:** Messages are durable, ensuring they are not lost if RabbitMQ restarts.
- **Dynamic Client Notifications:** Client consumers receive notifications specific to their placed orders via topic-based routing.

## Project Structure
```bash
rabbitmq/
├── .venv/                         # Python virtual environment
├── rabbitmq_order_module/
│   ├── init.py                # Makes 'rabbitmq_order_module' a Python package
│   ├── client_consumer.py         # Receives order status notifications for a specific client
│   ├── client_producer.py         # Handles client order creation and sending
│   ├── new_order_consumer.py      # Consumes new orders and processes them (stock reservation)
│   └── warehouse.py               # Manages product inventory (simulated)
└── README.md                      # This documentation file
```
## Prerequisites

Before running this project, ensure you have the following installed:

1.  **Python 3.7+:**
    * [Download Python](https://www.python.org/downloads/)
2.  **RabbitMQ Server:**
    * [Install RabbitMQ](https://www.rabbitmq.com/download.html)
    * Ensure RabbitMQ is running.
3.  **`pika` Python Library:**
    * Used for RabbitMQ interaction.

## Setup and Installation

1.  **Navigate to the project directory:**
    ```bash
    cd D:\learning\rabbitmq
    ```

2.  **Create and activate a Python virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # On Windows:
    .\.venv\Scripts\activate
    # On macOS/Linux:
    source ./.venv/bin/activate
    ```

3.  **Install required Python packages:**
    ```bash
    pip install pika
    ```

## How to Run

1.  **Ensure RabbitMQ Server is running.**

2.  **Open three separate terminal windows.**

3.  **Terminal 1: Order Processor (`new_order_consumer.py`):**
    ```bash
    cd D:\learning\rabbitmq
    python -m rabbitmq_order_module.new_order_consumer
    ```

4.  **Terminal 2: Client Notification Listener (`client_consumer.py`):**
    ```bash
    cd D:\learning\rabbitmq
    python -m rabbitmq_order_module.client_consumer
    ```

5.  **Terminal 3: Client Producer (`client_producer.py`):**
    ```bash
    cd D:\learning\rabbitmq
    python -m rabbitmq_order_module.client_producer
    ```
    Follow prompts to place an order. Observe messages in all terminals.

## System Flow

1.  **Client Producer:** Collects order details, generates `order_id` and `user_id`, and publishes JSON order messages to `new_orders_exchange` (direct, routing key `''`, persistent).
2.  **Order Consumer:** Consumes from `new_orders_queue` (bound to `new_orders_exchange`). It attempts to reserve stock via `Warehouse`.
3.  **On Stock Reservation Success:** Consumer `ack`s message, updates order status to 'processed', and publishes a notification to `notification_exchange` (topic) with routing key `client.<user_id>.order.<order_id>`.
4.  **On Stock Reservation Failure/Error:** Consumer `nack`s message (`requeue=False`).
5.  **Client Consumer:** Each instance creates an exclusive queue bound to `notification_exchange` with routing key `client.<its_user_id>.order.#`, receiving only notifications relevant to its `user_id`. It then prints the order status update.
6.  **Warehouse:** Manages a simulated in-memory product inventory, providing methods for `get_inventory()` and atomic `try_reserve_stock()`.

## RabbitMQ Components

| Component Name            | Type      | Purpose                                     | Binding/Usage                                                                  | Durability |
| :------------------------ | :-------- | :------------------------------------------ | :----------------------------------------------------------------------------- | :--------- |
| `new_orders_exchange`     | `direct`  | Producer sends new orders.                  | Producer publishes to it with `routing_key=''`.                              | Durable    |
| `notification_exchange`   | `topic`   | Consumer sends order status updates.        | Producer publishes with `routing_key='client.<user_id>.order.<order_id>'`. | Durable    |
| `new_orders_queue`        | Queue     | Stores new orders for processing.           | Bound to `new_orders_exchange` with `routing_key=''`.                        | Durable    |
| `amq.gen-XXXXXX` (client) | Queue     | Exclusive queue for each `ClientConsumer`. | Bound to `notification_exchange` with `routing_key='client.<user_id>.order.#'`. | Exclusive, Auto-Delete |

## Troubleshooting

* **`ModuleNotFoundError`**: Run scripts from `D:\learning\rabbitmq` using `python -m rabbitmq_order_module.your_script_name`.
* **No messages received**: Verify RabbitMQ is running. Check exchange names/types, queue bindings, and routing keys in all scripts match. Use RabbitMQ Management Plugin (`http://localhost:15672`).
* **Connection Refused**: RabbitMQ server is likely not running or accessible on `localhost:5672`.
* **Messages stuck in queue**: Check consumer's `_callback` for unhandled exceptions preventing `basic_ack`/`basic_nack`.

## Future Enhancements

* **Database Integration:** Replace in-memory `Warehouse` with a database.
* **Robust ID Generation:** Use UUIDs for `order_id`s and `user_id`s.
* **Dead Letter Queues (DLQs):** For failed message processing.
* **Logging:** Implement proper logging instead of `print()`.
* **Configuration:** Externalize RabbitMQ connection details.
* **Scaling:** Implement multiple consumers for `new_orders_queue`.
* **Persistent Client State:** If a `ClientConsumer` needs to remember its `user_id` across restarts.