# config.py
class Config:
    SECRET_KEY = 'your_super_secret_key' # Change this in production!
    # Add other common configurations here

class DevelopmentConfig(Config):
    DEBUG = True
    # Add development-specific configurations here

class ProductionConfig(Config):
    DEBUG = False
    # Add production-specific configurations here