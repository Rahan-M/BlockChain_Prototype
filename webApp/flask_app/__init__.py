# flask_app/__init__.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import asyncio, os
from blockchain.p2p import Peer

# --- Global State and Peer Management ---
# This dictionary will hold references to running peer tasks
# running_peer_tasks = {}

# async def _start_peer_in_background(host, port, name, miner):
#     """
#     Internal coroutine to start a peer and manage its lifecycle.
#     This runs as an asyncio Task.
#     """
#     miner_bool=False
#     if(miner=="True"):
#         miner_bool=True
#     peer_instance = Peer(host, port, name, miner_bool)
#     # Store the peer_instance directly, not just its task.
#     # This might be useful if you later need to access the Peer object itself
#     # (e.g., to query its state) from outside its task.
#     running_peer_tasks[name] = {"peer_instance": peer_instance}
#     try:
#         # Create the task for the peer's internal start method
#         task = asyncio.create_task(peer_instance.start())
#         running_peer_tasks[name]["task"] = task # Store the task object
#         await task # Wait for the peer's start() method to complete (or be cancelled)
#     except asyncio.CancelledError:
#         print(f"Peer task for '{name}' was cancelled. Stopping peer instance gracefully.")
#         # Ensure peer_instance.stop() is an awaitable if it performs async operations
#         # If it's synchronous, just call it: peer_instance.stop()
#         if asyncio.iscoroutinefunction(peer_instance.stop):
#             await peer_instance.stop()
#         else:
#             peer_instance.stop()
#     except Exception as e:
#         print(f"Error running peer '{name}': {e}")
#     finally:
#         # Clean up the entry from the global dictionary
#         if name in running_peer_tasks:
#             # Only delete if this specific task is still associated with the name
#             if "task" in running_peer_tasks[name] and running_peer_tasks[name]["task"] is task:
#                 del running_peer_tasks[name]
#         print(f"Peer '{name}' background task finished/cleaned up.")

# async def shutdown_all_peers():
#     """
#     Gracefully shuts down all active peer tasks.
#     This coroutine will be called during Hypercorn's graceful shutdown.
#     """
#     if not running_peer_tasks:
#         print("No peer tasks to shut down.")
#         return

#     print("Initiating graceful shutdown of all active peer tasks...")
#     tasks_to_cancel = []
#     for name, data in running_peer_tasks.items():
#         task = data.get("task")
#         if task and not task.done(): # Only consider active tasks
#             tasks_to_cancel.append(task)
#             print(f"  Cancelling task for peer: {name}")

#     if not tasks_to_cancel:
#         print("No active peer tasks found to cancel.")
#         return

#     for task in tasks_to_cancel:
#         task.cancel() # Request cancellation

#     try:
#         # Await all tasks to give them a chance to handle CancelledError
#         # `return_exceptions=True` prevents a single task's exception from stopping `gather`
#         # You might want to add a timeout here, e.g., asyncio.wait(tasks_to_cancel, timeout=5)
#         await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
#         print("All peer tasks gracefully shut down.")
#     except Exception as e:
#         print(f"Error during peer shutdown process: {e}")
#     finally:
#         running_peer_tasks.clear() # Clear the dictionary after shutdown is attempted

# Determine the directory where the Flask app.py is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Path to the React build directory relative to Flask app.py
# Assuming 'frontend/build' is where your React app gets built
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
    from .routes import chain_bp
    app.register_blueprint(chain_bp, url_prefix='/api/chain')
 

    return app