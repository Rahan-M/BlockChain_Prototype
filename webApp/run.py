# run.py
import asyncio, signal, argparse, os
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Import your app factory and the shutdown_all_peers function
from flask_app.app import create_app , shutdown_peer
from config import DevelopmentConfig # Import the desired configuration

import logging

# Set up basic logging to console
logging.basicConfig(level=logging.DEBUG) # Set to DEBUG for maximum verbosity

# Specifically configure websockets loggers
logging.getLogger('websockets.protocol').setLevel(logging.DEBUG)
logging.getLogger('websockets.server').setLevel(logging.DEBUG)
logging.getLogger('websockets.client').setLevel(logging.DEBUG)

async def main():
    parser=argparse.ArgumentParser(description="Handshaker")
    parser.add_argument("--port", type=int, required=True)
    
    args=parser.parse_args()

    # 1. Create your Flask application instance using the factory
    app = create_app(DevelopmentConfig)

    # 2. Configure Hypercorn
    hypercorn_config = Config()
    hypercorn_config.bind = [f"0.0.0.0:{args.port}"] # Listen on all interfaces on specified port
    hypercorn_config.accesslog = "-"          # Log access to stdout
    hypercorn_config.errorlog = "-"           # Log errors to stderr
    hypercorn_config.loglevel = "info"        # Set logging level
    hypercorn_config.workers = 1              # For development with shared state, keep at 1 worker.

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
        print(f"An unexpected error occurred in Hypercorn server: {e}")
    finally:
        # 7. After Hypercorn has stopped, initiate graceful shutdown of your peers
        
        print("Hypercorn server has finished. Initiating graceful peer shutdown.")
        await shutdown_peer()
        print("Application fully shut down.")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Path to the React build directory relative to Flask app.py
# Assuming 'frontend/build' is where your React app gets built
REACT_BUILD_DIR = os.path.join(BASE_DIR, 'flask_app', 'frontend', 'dist')

if __name__ == "__main__":
    # Ensure this is the main entry point to run the asyncio loop
    # asyncio.run() handles creating and closing the event loop for you.
    if not os.path.exists(REACT_BUILD_DIR):
        print(f"Error: React build directory not found at '{REACT_BUILD_DIR}'.")
        print("Please run 'npm install' and 'npm run build' in the 'frontend' directory first.")
        exit(1)
    asyncio.run(main())

