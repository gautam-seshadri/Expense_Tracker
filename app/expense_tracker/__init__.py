from flask import Flask
from datetime import timedelta
'''
1. Saving goals and tracking it
2. Recurring expenses -Done
3. Monthly exepnses limit and whether reached, reaching it or in track. - Done
4. Expense insights
'''

def create_app():
    app = Flask(__name__)

    # Configurations (optional, you can add more as needed)
    app.config['SECRET_KEY'] = '654321'  # Replace with your secret key
    app.permanent_session_lifetime = timedelta(days=10)

    # Register blueprints
    from .routes import main
    from .routes_fb import main as fb_main
    app.register_blueprint(main)
    app.register_blueprint(fb_main, url_prefix='/food')

    return app
