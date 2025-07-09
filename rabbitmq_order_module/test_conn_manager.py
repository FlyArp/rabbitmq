# rabbitmq_order_module/connection_manager.py (UPDATED - No Logging)

import pika
import threading
import time
import concurrent.futures

# Assuming you have a config.py with RabbitMQ connection details
# For this example, I'll use hardcoded values if config.py is not available

class TestConnectionManager:
    """
    A singleton class to manage a single, robust connection to RabbitMQ
    across multiple threads using pika.BlockingConnection.
    Provides thread-local channels.
    """
    _instance = None
    _connection = None
    _lock = threading.Lock()  # Protects _connection and _is_connecting
    _is_connecting = False  # Flag to prevent multiple concurrent connection attempts
    _channel_local = threading.local()  # Stores a channel for each thread

    def __new__(cls):
        """Implements the singleton pattern with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TestConnectionManager, cls).__new__(cls)
                    cls._instance._init_once()  # Initialize on first instance creation
        return cls._instance

    def _init_once(self):
        """Initializes attributes only once for the singleton instance."""
        if hasattr(self, '_initialized_flag') and self._initialized_flag:
            return

        self._initialized_flag = True  # Use a distinct flag to indicate initialization
        self._connection = None
        self._is_connecting = False
        self._reconnect_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1,
                                                                         thread_name_prefix="ReconnectThread")
        print(" [x] ConnectionManager initialized (singleton).")

    def _get_connection_parameters(self):
        """Helper to get pika connection parameters from config."""
        return pika.ConnectionParameters(
            host='localhost',
        )

    def _on_connection_closed_callback(self, reply_code, reply_text):
        """
        Callback invoked by BlockingConnection when the connection is unexpectedly closed.
        Note: This callback is very limited. It doesn't get the connection object.
        """
        print(f" [!] Connection closed unexpectedly: ({reply_code}) {reply_text}. Triggering reconnect...")
        # Mark the connection as bad so get_channel will try to reconnect
        with self._lock:
            if self._connection:
                try:
                    self._connection.close()  # Ensure it's fully closed if possible
                except pika.exceptions.ConnectionClosedByBroker:
                    pass  # Already closed
                except Exception as e:
                    print(f" [!] Error during explicit close in _on_connection_closed_callback: {e}")
            self._connection = None
            self._is_connecting = False  # Reset flag to allow new connection attempts
        self._start_reconnect_loop()  # Start the reconnect loop in background

    def _connect_blocking_attempt(self):
        """
        Attempts to establish a new BlockingConnection.
        Returns the connection object on success, None on failure.
        """
        try:
            connection_params = self._get_connection_parameters()
            print(" [x] Attempting to establish BlockingConnection...")
            # Pass the on_close_callback to the constructor
            connection = pika.BlockingConnection(
                parameters=connection_params,
                on_close_callback=self._on_connection_closed_callback
            )
            print(f" [x] Successfully established BlockingConnection. Connection is_open: {connection.is_open}")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            print(f" [!] AMQPConnectionError during BlockingConnection attempt: {e}")
            return None
        except Exception as e:
            print(f" [!] Unexpected error during BlockingConnection attempt: {e}")
            return None

    def _start_reconnect_loop(self):
        """
        Submits the reconnection loop to the ThreadPoolExecutor if not already running.
        """
        with self._lock:
            if not self._is_connecting:
                self._is_connecting = True
                print(" [x] Initiating background reconnection process...")
                self._reconnect_executor.submit(self._reconnect_async_loop)
            else:
                print(" [x] Reconnection process already active.")

    def _reconnect_async_loop(self):
        """
        Background loop to attempt reconnection until successful.
        This runs in a separate thread managed by the executor.
        """
        retry_count = 0
        retry_delay_base = 5  # Start with a longer delay for background retries
        max_delay = 60  # Max 1 minute delay

        while True:
            with self._lock:
                if self._connection and self._connection.is_open:
                    self._is_connecting = False
                    print(" [x] Background reconnect successful and connection is open.")
                    return  # Exit the reconnect loop

            try:
                # Wait before the next attempt, especially after a failure
                delay = retry_delay_base * (2 ** retry_count)
                delay = min(delay, max_delay)
                print(f" [x] Background reconnect attempt {retry_count + 1}. Retrying in {delay:.1f}s...")
                time.sleep(delay)

                new_connection = self._connect_blocking_attempt()
                if new_connection:
                    with self._lock:  # Acquire lock to update _connection safely
                        self._connection = new_connection

                    print(" [x] Background reconnect successful!")
                    with self._lock:  # Acquire lock to update _is_connecting safely
                        self._is_connecting = False
                    return  # Exit loop on success
                else:
                    retry_count += 1  # Failed to create connection object

            except Exception as e:
                print(f" [!] Unexpected error during background reconnect loop: {e}")
                retry_count += 1  # Treat as a failed attempt

    def get_channel(self):
        """
        Provides a thread-local channel. Ensures connection is active.
        If connection is down, it triggers or waits for reconnection.
        """
        with self._lock:  # Acquire lock to manage shared connection state
            # Loop to ensure we get a valid connection before trying to create a channel
            while not self._connection or not self._connection.is_open:
                print(" [!] Connection not active or not open. Attempting to connect/wait...")
                if not self._is_connecting:
                    # If no connection object exists, try to create one blocking
                    self._connection = self._connect_blocking_attempt()
                    if not self._connection:
                        # If initial blocking attempt fails, start background loop
                        print(" [!] Initial blocking connection attempt failed. Starting background reconnect loop.")
                        self._start_reconnect_loop()
                    else:
                        # If initial attempt succeeded, we can proceed
                        print(" [x] Initial blocking connection successful. Proceeding to get channel.")
                        break  # Exit the while loop as connection is now available

                print(" [x] Waiting for background connection to restore...")
                time.sleep(1)  # Wait for the background reconnect loop to establish a connection

            # At this point, self._connection should be open

            # Check for thread-local channel
            if not hasattr(self._channel_local, "channel") or \
                    self._channel_local.channel is None or \
                    not self._channel_local.channel.is_open:  # Use channel.is_open
                try:
                    print(f" [x] Opening new channel for thread {threading.current_thread().name}...")
                    self._channel_local.channel = self._connection.channel()
                    print(
                        f" [x] Channel opened for thread {threading.current_thread().name}. Channel is_open: {self._channel_local.channel.is_open}")
                    return self._channel_local.channel
                except pika.exceptions.ChannelClosedByBroker as e:
                    print(
                        f" [!] Channel closed by broker unexpectedly for thread {threading.current_thread().name}: {e}. Attempting to re-open channel.")
                    self._channel_local.channel = None  # Clear bad channel
                    # Propagate error so calling code can retry getting a channel if needed
                    # or re-call get_channel, which will now try to open a new one.
                    raise ConnectionError("Channel was closed by broker. Please retry channel acquisition.") from e
                except pika.exceptions.AMQPConnectionError as e:
                    print(
                        f" [!] AMQP connection error when opening channel for thread {threading.current_thread().name}: {e}. Triggering full connection reset.")
                    with self._lock:  # Acquire lock to reset connection state
                        if self._connection:
                            try:
                                self._connection.close()  # Close the problematic connection
                            except:
                                pass  # Ignore errors during close if connection is already bad
                        self._connection = None  # Mark for full reconnection
                        self._is_connecting = False
                    self._channel_local.channel = None  # Clear bad channel
                    # Recurse: This will re-enter the outer while loop and trigger a new connection attempt
                    return self.get_channel()
                except Exception as e:
                    print(f" [!] Error opening channel for thread {threading.current_thread().name}: {e}")
                    self._channel_local.channel = None
                    raise  # Re-raise other unexpected errors

            return self._channel_local.channel

    def close_connection(self):
        """Closes the main RabbitMQ connection and shuts down the executor."""
        with self._lock:
            if self._connection and self._connection.is_open:
                print(" [x] Closing RabbitMQ connection gracefully...")
                try:
                    self._connection.close()
                    print(" [x] RabbitMQ connection closed.")
                except Exception as e:
                    print(f" [!] Error closing RabbitMQ connection: {e}")
            self._connection = None
            self._is_connecting = False

            # Shut down the reconnect executor
            if self._reconnect_executor:
                print(" [x] Shutting down reconnect executor...")
                self._reconnect_executor.shutdown(wait=True,
                                                  cancel_futures=True)  # cancel_futures ensures background loop stops
                print(" [x] Reconnect executor shut down.")

# --- Example Usage (for testing purposes