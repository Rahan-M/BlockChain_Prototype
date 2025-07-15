# flask_app/__init__.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import asyncio, os
from blockchain.pow import p2p

consensus=''
def set_consensus(str):
    global consensus
    consensus=str

async def shutdown_peer():
    if(consensus=='pow'):
        from flask_app.controllers.pow_controllers import peer_instance
        if not peer_instance:
            return jsonify({"success":True, "msg":"No Peer Running"})
            
        try:
            if(peer_instance):
                await peer_instance.stop()
            return jsonify({"success":True, "msg":"Peer succesfully shut down"})
        
        except Exception as e:
            print(f"Error during peer shutdown process: {e}")
            return jsonify({"success":False, "msg":"Some error occured during shut down"})
        
        finally:
            set_consensus('')
            peer_instance=None

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

    @app.route('/api/stop', methods=['GET'])
    async def shut_curr_peer():
        return await shutdown_peer()

    # Import and register blueprints INSIDE the factory function
    from .routes.pow_routes import chain_bp
    app.register_blueprint(chain_bp, url_prefix='/api/pow')
 

    return app