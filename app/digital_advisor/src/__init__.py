import os
from flask import Flask, render_template, request, jsonify
from .extensions import db, migrate, jwt, cors
from .config import Config
from .routes.auth_routes import auth_bp
from .routes.portfolio_routes import portfolio_bp
from .routes.price_routes import price_bp
from .routes.prediction_routes import prediction_bp
from .routes.balance_routes import balance_bp
from .routes.transaction_routes import transaction_bp


def create_app():
    app = Flask(__name__,
                static_folder='static',    # Serve static files from app/static
                template_folder='templates') # Serve HTML templates from app/templates
    
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)  # Enable CORS for the app

    # # Load models (commented out as per your provided code)
    # model_dir = app.config.get("MODEL_DIRECTORY")
    # app.models = load_models_from_directory(model_dir)

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(price_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(balance_bp)
    app.register_blueprint(transaction_bp)

    # Frontend routes (serving HTML pages)
    @app.route('/')
    def index():
        """Landing page"""
        return render_template('index.html')
    
    @app.route('/login')
    def login_page():
        """Login page"""
        return render_template('login.html')
    
    @app.route('/register')
    def register_page():
        """Registration page"""
        return render_template('register.html')
    
    @app.route('/dashboard')
    def dashboard_page():
        """Dashboard page (authentication handled by frontend JS)"""
        return render_template('dashboard.html')
    
    @app.route('/profile')
    def profile_page():
        """User profile page"""
        return render_template('profile.html')
    
    @app.route('/history')
    def history_page():
        """User transaction history page"""
        return render_template('history.html')
    
    @app.route('/portfoliopage')
    def portfolio_page():
        """User portfolio page"""
        return render_template('portfoliopage.html')
    
    # Error handlers for better API/frontend separation
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors differently for API vs frontend routes"""
        if (request.path.startswith('/api/') or 
            request.path.startswith('/auth/') or 
            request.path.startswith('/portfolio/') or
            request.path.startswith('/prediction/') or # NEW: Add transaction route
            request.path.startswith('/transactions/')):
            return jsonify({'msg': 'Endpoint not found'}), 404
        
        # For frontend routes, try to serve 404 page or redirect to home
        try:
            return render_template('404.html'), 404
        except:
            # If 404.html doesn't exist, redirect to home
            return render_template('index.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        if (request.path.startswith('/api/') or 
            request.path.startswith('/auth/') or 
            request.path.startswith('/portfolio/') or
            request.path.startswith('/prediction/') or # NEW: Add transaction route
            request.path.startswith('/transactions/')):
            return jsonify({'msg': 'Internal server error'}), 500
        
        try:
            return render_template('500.html'), 500
        except:
            return jsonify({'msg': 'Internal server error'}), 500
    
    return app

# If you run your app directly using `python app.py` for local development
if __name__ == '__main__':
    app = create_app()
    # IMPORTANT: use_reloader=False is crucial with APScheduler
    # as it prevents duplicate jobs from being scheduled when Flask reloads.
    app.run(debug=True, use_reloader=False) 

