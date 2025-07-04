# run.py
import asyncio
import signal
import sys
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Import your app factory and the shutdown_all_peers function
from flask_app import create_app, shutdown_all_peers
from config import DevelopmentConfig # Import the desired configuration

async def main():
    # 1. Create your Flask application instance using the factory
    app = create_app(DevelopmentConfig)

    # 2. Configure Hypercorn
    hypercorn_config = Config()
    hypercorn_config.bind = ["0.0.0.0:8000"] # Listen on all interfaces on port 8000
    hypercorn_config.accesslog = "-"          # Log access to stdout
    hypercorn_config.errorlog = "-"           # Log errors to stderr
    hypercorn_config.loglevel = "info"        # Set logging level
    hypercorn_config.workers = 1              # For development with shared state, keep at 1 worker.
                                              # Multi-worker setups complicate shared `running_peer_tasks`.

    # 3. Create an asyncio.Event to signal Hypercorn to shut down
    shutdown_event = asyncio.Event()

    # 4. Define a signal handler
    def signal_handler(*args):
        print("\nReceived OS shutdown signal (SIGINT/SIGTERM). Setting Hypercorn shutdown event...")
        shutdown_event.set() # Set the event to trigger Hypercorn's graceful shutdown

    # 5. Register the signal handler with the current asyncio event loop
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler, sig, None)
        except NotImplementedError:
            # add_signal_handler is not available on all platforms (e.g., Windows for SIGTERM)
            print(f"Warning: Signal handler for {sig.name} not supported on this platform.")
            # On Windows, Ctrl+C (SIGINT) usually works, but SIGTERM might not be caught this way.
            # For production on Windows, consider service managers or alternative signal handling.

    print(f"Starting Hypercorn server on {hypercorn_config.bind[0]}...")
    try:
        # 6. Run Hypercorn's serve function
        # The `shutdown_trigger` is an awaitable that, when it resolves, tells Hypercorn to shut down.
        # In our case, it's `shutdown_event.wait()`, which resolves when `shutdown_event.set()` is called.
        await serve(app, hypercorn_config, shutdown_trigger=shutdown_event.wait)
    except asyncio.CancelledError:
        print("Hypercorn server task was cancelled.")
    except Exception as e:
        print(f"An unexpected error occurred in Hypercorn serve: {e}")
    finally:
        # 7. After Hypercorn has stopped, initiate graceful shutdown of your peers
        print("Hypercorn server has finished. Initiating graceful peer shutdown.")
        await shutdown_all_peers()
        print("Application fully shut down.")

if __name__ == "__main__":
    # Ensure this is the main entry point to run the asyncio loop
    # asyncio.run() handles creating and closing the event loop for you.
    asyncio.run(main())

# Do NOT call app.run() here if you are using async functions.
# Instead, you will run this file using an ASGI server from the terminal.

# Example of how you would run it from the terminal:
# For development with auto-reloading:
# hypercorn run:app --bind 0.0.0.0:8093 --reload

# For production (using gunicorn with uvicorn worker):
# gunicorn run:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8093