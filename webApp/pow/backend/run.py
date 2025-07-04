# run.py
from flask_app import create_app # Import the factory function
from config import DevelopmentConfig # Import the desired configuration

# Create the app instance using the factory
app = create_app(DevelopmentConfig)

# Do NOT call app.run() here if you are using async functions.
# Instead, you will run this file using an ASGI server from the terminal.

# Example of how you would run it from the terminal:
# For development with auto-reloading:
# hypercorn run:app --bind 0.0.0.0:8093 --reload

# For production (using gunicorn with uvicorn worker):
# gunicorn run:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8093