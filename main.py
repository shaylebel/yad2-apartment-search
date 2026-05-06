import sys
import os
import logging

os.chdir(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from web.app import create_app

app = create_app(settings)

if __name__ == "__main__":
    print(f"Starting Yad2 Apartment Search at http://{settings.flask_host}:{settings.flask_port}")
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=False,
    )
