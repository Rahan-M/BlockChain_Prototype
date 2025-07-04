# flask_app/controllers.py
from flask import request, jsonify
import asyncio

# Import running_peer_tasks and _start_peer_in_background from the application's __init__.py
from .__init__ import running_peer_tasks, _start_peer_in_background

# Assuming Blueprint is correctly imported and defined in routes.py
# If you define bp directly here, make sure to import it correctly in routes.py
# from flask import Blueprint
# bp = Blueprint('main', __name__) # If you put blueprint creation here

# However, based on your routes.py, the blueprint 'chain_bp' is defined there.
# This file defines the *logic* for the routes, not the blueprint itself.

async def start_new_blockchain():
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = data.get('port')
        host = data.get('host')
        miner = data.get('miner')

        if name in running_peer_tasks and running_peer_tasks[name].get("task") and not running_peer_tasks[name]["task"].done():
            return jsonify({"error": f"Peer '{name}' is already running."}, 409)

        # Use the _start_peer_in_background function imported from __init__.py
        asyncio.create_task(_start_peer_in_background(host, port, name, miner))

        return jsonify({"message": f"Peer '{name}' is being started in the background on {host}:{port}"})
    else:
        return jsonify({"error": "Request must be JSON"}, 400)