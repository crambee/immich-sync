import configparser
from pathlib import Path
from dataclasses import dataclass


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


@dataclass
class Config:
    url: str
    apikey: str
    photodir: Path
    album: str
    raw: bool


def load_config(path: str) -> Config:
    """
    Load and validate the Immich sync configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ConfigError: For missing sections, keys, or invalid values.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    parser = configparser.ConfigParser()
    parser.read(path)

    if "immich" not in parser:
        raise ConfigError("Missing 'immich' section in config file.")
    sec = parser["immich"]

    required = ["url", "apikey", "photodir", "album", "raw"]
    missing = [key for key in required if key not in sec]
    if missing:
        raise ConfigError(
            f"Missing required config keys in 'immich' section: {', '.join(missing)}"
        )

    url = sec["url"].strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ConfigError(f"Invalid URL in config: {url}")

    apikey = sec["apikey"].strip()
    if not apikey:
        raise ConfigError("API key cannot be empty.")

    dest = Path(sec["photodir"].strip())
    if not dest.parent.exists():
        # Attempt to create directories later in downloader, but warn now
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigError(
                f"Cannot create destination directory: {dest.parent} ({e})"
            )

    album = sec["album"].strip()
    if not album:
        raise ConfigError("Album name cannot be empty.")

    try:
        raw = parser.getboolean("immich", "raw")
    except ValueError:
        raise ConfigError("Invalid boolean value for 'raw'; expected true or false.")

    return Config(
        url=url,
        apikey=apikey,
        photodir=dest,
        album=album,
        raw=raw,
    )
