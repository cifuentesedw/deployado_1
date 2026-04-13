import os
from dotenv import load_dotenv

# Carga el .env ANTES de importar la app
load_dotenv()

from app import create_app

# AWS Elastic Beanstalk busca un objeto llamado 'application'
application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    application.run(host="0.0.0.0", port=port, debug=debug)
