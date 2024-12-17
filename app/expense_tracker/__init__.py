from flask import Flask


def create_app():
    app = Flask(__name__)

    # Configurations (optional, you can add more as needed)
    app.config['SECRET_KEY'] = '654321'  # Replace with your secret key

    # Register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app
