import threading
from flask import Flask


def create_app(settings):
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SETTINGS"] = settings
    app.config["SCRAPE_STATUS"] = {
        "running": False,
        "progress": "",
        "error": None,
        "count": 0,
    }
    app.config["SCRAPE_LOCK"] = threading.Lock()

    from web.routes import bp
    app.register_blueprint(bp)

    return app
