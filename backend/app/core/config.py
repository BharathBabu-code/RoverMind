import os
from pathlib import Path
from dotenv import load_dotenv

# Determine the repository root dynamically based on this file's location.
# __file__ is backend/app/core/config.py
# parents[0] = core, parents[1] = app, parents[2] = backend, parents[3] = project root
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_DIR / ".env"

# Load environment variables from the root .env file.
# override=False ensures we do not overwrite variables already set in the OS environment.
load_dotenv(dotenv_path=ENV_PATH, override=False)

class Settings:
    def __init__(self) -> None:
        # Read the API key safely. Defaults to None if missing.
        self._meta_api_key: str | None = os.environ.get("META_API_KEY")

    @property
    def is_meta_api_configured(self) -> bool:
        """
        Check if the Meta API key is available and not just empty whitespace.
        Returns False if the key is missing, empty, or contains only whitespace.
        Does not validate if the key is authentic.
        """
        if not self._meta_api_key:
            return False
        return bool(self._meta_api_key.strip())

# Expose a singleton instance for the application to import.
settings = Settings()