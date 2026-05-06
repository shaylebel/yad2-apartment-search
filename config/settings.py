from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    yad2_email: str
    yad2_password: str

    headless: bool = True
    browser_data_dir: str = "./browser_data"
    slow_mo: int = 100

    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 5.0
    max_pages_per_search: int = 10

    db_path: str = "./data/listings.db"

    flask_host: str = "127.0.0.1"
    flask_port: int = 5000
    flask_debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
