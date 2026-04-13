import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()


def _build_db_url(raw: str) -> str:
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if raw.startswith(prefix):
            return "postgresql+psycopg://" + raw[len(prefix):]
    return raw


def create_app(config_name=None):
    app = Flask(__name__)

    raw_db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/blacklist_db",
    )
    db_url = _build_db_url(raw_db_url)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # pool_timeout solo aplica a PostgreSQL, no a SQLite (tests)
    if db_url.startswith("postgresql"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"connect_timeout": 10},
            "pool_timeout": 10,
            "pool_pre_ping": True,
        }

    app.config["STATIC_TOKEN"] = os.environ.get(
        "STATIC_TOKEN", "my-super-secret-static-token-2024"
    )
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "jwt-secret-key-blacklist-service-2024"
    )

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)

    api = Api(app)
    from app.resources.blacklist import BlacklistResource, BlacklistCheckResource
    api.add_resource(BlacklistResource, "/blacklists")
    api.add_resource(BlacklistCheckResource, "/blacklists/<string:email>")

    from flask import jsonify

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "service": "blacklist-microservice"}), 200

    with app.app_context():
        if db_url.startswith("postgresql"):
            print(f"⏳ Conectando a la base de datos...")
            print(f"   {db_url[:70]}...")
        try:
            db.create_all()
            if db_url.startswith("postgresql"):
                print("✅ Base de datos conectada y tablas listas.")
        except Exception as e:
            print(f"❌ Error al conectar con la base de datos: {e}")
            raise

    return app
