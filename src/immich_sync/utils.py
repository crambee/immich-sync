import hashlib
import base64
from pathlib import Path


def delete_orphans(photodir: Path, valid_names: set[str]):
    """
    Remove any file in photodir whose name is not in valid_names.
    """
    for f in photodir.iterdir():
        if f.is_file() and f.name not in valid_names:
            f.unlink()


def compute_checksum(file_path: Path) -> str:
    """
    Compute the SHA1 checksum of the file and return it
    as a base64-encoded string.
    """
    hasher = hashlib.sha1()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return base64.b64encode(hasher.digest()).decode("utf-8")
