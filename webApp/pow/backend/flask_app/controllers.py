from flask import render_template, request, redirect, url_for, flash, jsonify
from ..p2p import Peer
import asyncio

running_peer_tasks={}
async def _start_peer_in_background(host, port, name, miner):
    peer_instance = Peer(host, port, name, miner)
    try:
        task = asyncio.create_task(peer_instance.start())
        running_peer_tasks[name]["task"] = task # Store the task
        await task # This will keep this async function running until the peer stops
    except asyncio.CancelledError:
        print(f"Peer task for '{name}' was cancelled.")
        peer_instance.stop() # Signal the peer to stop its internal loop
    except Exception as e:
        print(f"Error running peer '{name}': {e}")
    finally:
        if name in running_peer_tasks:
            del running_peer_tasks[name] # Clean up
        print(f"Peer '{name}' background task finished/cleaned up.")

async def start_new_blockchain():
    if(request.method=='POST' and request.is_json):
        data = request.get_json()
        # Or simply: data = request.json
        name = data.get('name')
        port = data.get('port')
        host = data.get('host')
        miner = data.get('miner')

        if name in running_peer_tasks and running_peer_tasks[name]["task"] and not running_peer_tasks[name]["task"].done():
            return jsonify({"error": f"Peer '{name}' is already running."}, 409)


        # Create the background task for the peer.
        # We don't await it here, so the API call returns immediately.
        asyncio.create_task(_start_peer_in_background(host, port, name, miner))

        return jsonify({"message": f"Peer '{name}' is being started in the background on {host}:{port}"})
    else:
        return jsonify({"error": "Request must be JSON"}, 400)