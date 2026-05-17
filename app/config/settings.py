import os

class Config:

    SECRET_KEY = (
        "qdtOmkgnGkKziwPQM4kvZmMf"
    )
    # Error handling - PROPAGATE_EXCEPTIONS=True agar Flask catch semua exception
    PROPAGATE_EXCEPTIONS = True
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True
    JSON_SORT_KEYS = False
    EXPLAIN_TEMPLATE_LOADING = False
    
    # Database connection pool configuration
    # pool_pre_ping: test connection sebelum digunakan
    # pool_recycle: recycle connection setiap 3600 detik (1 jam)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 5,  # Timeout 5 detik untuk koneksi
        }
    }
    
    # Server Configuration
    SERVER_HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
    SERVER_PORT = int(os.environ.get('FLASK_PORT', 5000))