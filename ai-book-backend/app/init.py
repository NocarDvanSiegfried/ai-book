# Подтягиваем .env для всего бекенда (по желанию)
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception:
    pass

__all__ = ["__version__"]
__version__ = "1.0.0"
