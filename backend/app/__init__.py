from flask import Flask
from flask_cors import CORS
from .routes import bp as api_bp   # <-- DO NOT comment this out

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)  # <-- 'api_bp' comes from routes.py
    return app