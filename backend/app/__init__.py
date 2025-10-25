from flask import Flask
from flask_cors import CORS
from .routes import bp as api_bp

def create_app():
    app = Flask(__name__)
    CORS(app)  # allow your extension to call localhost during dev
    app.register_blueprint(api_bp)
    return app