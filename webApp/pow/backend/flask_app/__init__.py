# flask_app/__init__.py
from flask import Flask
from flask_cors import CORS
# No direct import of DevelopmentConfig or chain_bp here.
# They will be imported inside create_app or in run.py

def create_app(config_class=None):
    app = Flask(__name__)
    CORS(app)

    if config_class:
        app.config.from_object(config_class)
    else:
        # Default to DevelopmentConfig if no config_class is provided
        # This import is here to avoid circular dependency if config.py imports anything from app
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Import and register blueprints INSIDE the factory function
    # This avoids circular import issues if routes.py needs to import 'app' or other app-related objects
    from .routes import chain_bp # Note the relative import: .routes
    app.register_blueprint(chain_bp, url_prefix='/api/chain')

    return app

# Do NOT define 'app = create_app()' directly here.
# This will be done in your run.py or directly by your ASGI server.
# replace this
# app.run(host="0.0.0.0", port=8093)

#with this in the terminal
#hypercorn my_app:app --bind 0.0.0.0:8093 --reload

