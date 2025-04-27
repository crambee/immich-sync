# immich_sync/cli.py

import sys
import click
from pathlib import Path
from .config import load_config, ConfigError, Config
from .downloader import sync_album


@click.command()
@click.option(
    "--config", "-c", default="config.ini", help="Path to config file (optional)"
)
@click.option("--url", help="Immich server URL")
@click.option("--apikey", help="API key")
@click.option("--photodir", help="Local folder to sync into")
@click.option("--album", help="Album name to sync")
@click.option(
    "--raw/--no-raw",
    default=None,
    help="Extract RAW thumbnails? Overrides config if set.",
)
def main(config, url, apikey, photodir, album, raw):
    """
    Sync an Immich album to a local directory.
    You can either supply a config.ini file, or pass everything on the CLI.
    """
    # 1) Try to load from config file (if it exists).
    cfg_file = Path(config)
    base = None
    if cfg_file.exists():
        try:
            base = load_config(config)
        except (FileNotFoundError, ConfigError) as e:
            click.echo(f"Config error: {e}", err=True)
            sys.exit(1)

    # 2) Merge CLI args on top of file (or build straight from CLI if no file).
    final = {
        "url": url or (base.url if base else None),
        "apikey": apikey or (base.apikey if base else None),
        "photodir": Path(photodir) if photodir else (base.photodir if base else None),
        "album": album or (base.album if base else None),
        "raw": raw if raw is not None else (base.raw if base else False),
    }

    # 3) Make sure we have everything we need.
    missing = [k for k, v in final.items() if v is None]
    if missing:
        click.echo(f"Missing required parameters: {', '.join(missing)}", err=True)
        sys.exit(1)

    # 4) Build a validated Config object
    try:
        cfg = Config(**final)
    except TypeError as e:
        click.echo(f"Internal error building config: {e}", err=True)
        sys.exit(1)

    # 5) Run sync
    try:
        downloaded = sync_album(cfg)
        click.echo(f"✔ Done! Synced {len(downloaded)} assets.")
    except Exception as e:
        click.echo(f"Error during sync: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
