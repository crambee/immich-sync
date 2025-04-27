# immich-sync

`immich-sync` is a simple Python CLI tool for synchronizing photos from an [Immich](https://immich.dev/) server to a local directory. It supports album selection, checksum-based incremental downloads, and optional RAW image extraction.

## Features

- Incremental sync (download-only) using SHA-1 checksums
- Concurrent downloads with progress bars
- Optional RAW thumbnail extraction (requires extra dependencies)
- Configurable via `config.ini` or command-line flags

## Installation

Install from PyPI (if published) or locally via pip:

```bash
# From PyPI
pip install immich-sync

# From local source
git clone https://github.com/youruser/immich-sync.git
cd immich-sync
pip install .[raw]  # include RAW support
```

> **Note:** RAW thumbnail extraction requires the `rawpy` and `imageio` packages. Install with the `[raw]` extra as shown above.

## Configuration

`immich-sync` can be configured either via a `config.ini` file or command-line options.

### Sample `config.ini`

```ini
[immich]
url = https://your.immich.server
apikey = YOUR_API_KEY
# Local folder where photos will be saved
imagedir = /path/to/photos
# Name of the album to sync
album = Vacation 2024
# Download from RAW files? true or false
raw = true
```

### Command-line overrides

All fields can be overridden on the CLI:

```bash
immich-sync \
  --url https://different.immich.server \
  --apikey YOUR_API_KEY \
  --imagedir /path/to/photos \
  --album "Vacation 2025" \
  --raw
```

These take precedence over the config file, which allows for a hybrid approach. A common usage pattern is to keep the url and apikey in the config file, with album and imagedir passed as CLI args.

## Usage

Run the sync with either config file or CLI flags:

```bash
# Using config file
immich-sync -c config.ini

# Using CLI arguments
immich-sync \
  --url https://your.immich.server \
  --apikey YOUR_API_KEY \
  --imagedir /path/to/photos \
  --album "Vacation 2024" \
  --raw
```

> **Note:** By default the tool will parse any file named `config.ini` in the current working directory.

Example output:

```
Downloading AssetInfo: 10 assets [================================] 100%
Processing Checksums: 10 assets [==============================] 100%
Overall Download:  75%|=======    | 750M/1.00G [03:45<01:15, 3.2MB/s]
✔ Done! Synced 10 assets.
```

## Development & Testing

All development was done on Linux, with no experimentation on other platforms. There is currently no tests for this tool.
`uv` is used for dependency management as a poetry alternative.

```bash
# install uv
pip install uv

# (optional) create a virtual environment and source it
uv venv
source .venv/bin/activate

# install all dependencies
uv sync --extra dev

# (optional) install pre-commit hooks
pre-commit install

# run the tool
uv run immich-sync {args}
```
