# flask_app/__init__.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import asyncio, os
from blockchain.pow import p2p
import threading
peer_instance: p2p.Peer=None
peer_task=None

def _start_peer_in_background(host, port, name, miner, bootstrap_host=None, boostrap_port=None):
    """
    Internal coroutine to start a peer and manage its lifecycle.
    This runs as an asyncio Task.
    """
    global peer_instance
    miner_bool=p2p.strtobool(miner)
    peer_instance = p2p.Peer(host, port, name, miner_bool)
    try:
        # Create the task for the peer's internal start method
        asyncio.run(peer_instance.start(bootstrap_host, boostrap_port)) # hit here is printed if this is not in create task
        print(f"[{name}] Peer instance start method completed normally.")

    except asyncio.CancelledError:
        print(f"Peer task for '{name}' was cancelled. Stopping peer instance gracefully.")
        # Ensure peer_instance.stop() is an awaitable if it performs async operations
        # If it's synchronous, just call it: peer_instance.stop()
        if asyncio.iscoroutinefunction(peer_instance.stop):
            peer_instance.stop()
        else:
            peer_instance.stop()

    except Exception as e:
        print(f"Error running peer '{name}': {e}")
    finally:
        # Clean up the entry from the global dictionary
        peer_instance=None
        print(f"Peer '{name}' background task finished/cleaned up.")

async def shutdown_peer():
    """
    Gracefully shuts down all active peer tasks.
    This coroutine will be called during Hypercorn's graceful shutdown.
    """
    if not peer_instance:
        print("No peer tasks to shut down.")
        return

    print("Initiating graceful shutdown of all active peer tasks...")

    try:
        peer_instance.stop()
    except Exception as e:
        print(f"Error during peer shutdown process: {e}")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Path to the React build directory relative to Flask app.py
REACT_BUILD_DIR = os.path.join(BASE_DIR, 'frontend', 'dist')
# --- Flask App Factory ---
def create_app(config_class=None):
    app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path='/')
    CORS(app)

    if config_class:
        app.config.from_object(config_class)
    else:
        # Default to DevelopmentConfig if no config_class is provided
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        """
        Serves the static files of the React application.
        If the path is empty or points to a file, it serves the file.
        Otherwise, it serves index.html (for client-side routing).
        """
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')

    # Import and register blueprints INSIDE the factory function
    from .routes.pow_routes import chain_bp
    app.register_blueprint(chain_bp, url_prefix='/api/pow')
 

    return app