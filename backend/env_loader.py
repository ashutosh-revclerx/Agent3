from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """
    Load backend environment variables from backend/.env only.
    """
    backend_dir = Path(__file__).resolve().parent
    backend_env = backend_dir / ".env"

    load_dotenv(backend_env, override=True)
