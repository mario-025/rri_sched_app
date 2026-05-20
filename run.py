import os
from app import create_app
from app.config.settings import Config

app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    use_reloader = os.environ.get('FLASK_USE_RELOADER', 'false').lower() == 'true'
    app.run(
        debug=debug_mode,
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        use_reloader=use_reloader
    )
