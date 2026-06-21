import os

class Config:

    SECRET_KEY = (
        "8ab7c0d6-26f5-4862-8544-aa5ff7494960"
    )
    PROPAGATE_EXCEPTIONS = True
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    JSON_SORT_KEYS = False
    EXPLAIN_TEMPLATE_LOADING = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 5, 
        }
    }
    
    # Server Configuration
    SERVER_HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    SERVER_PORT = int(os.environ.get('FLASK_PORT', 5000))