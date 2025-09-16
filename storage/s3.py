"""Simple file storage abstraction.

In this proof of concept we use the local filesystem to store uploaded
evidence.  The `save_evidence_file` function writes the bytes to a file in
the configured directory, computes a hash of the contents and returns the
path and hash.  In a production deployment this module could be replaced
with an S3 client (such as boto3) using the credentials provided via
environment variables.
"""

from __future__ import annotations

import hashlib
import os
from typing import Tuple

from app.settings import get_settings


def save_evidence_file(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """Persist an uploaded file and return its path and content hash.

    Args:
        file_bytes: The raw bytes of the uploaded file.
        filename: The original filename provided by the user.  The basename
            of this filename will be used when storing the file on disk.

    Returns:
        A tuple of `(storage_path, hex_hash)`, where `storage_path` is the
        filesystem location where the file was written and `hex_hash` is the
        MD5 hash of the file contents.  If the configured storage directory
        does not exist it will be created.
    """

    settings = get_settings()
    storage_dir = settings.evidence_storage_dir
    os.makedirs(storage_dir, exist_ok=True)
    # compute MD5 hash of the file contents
    digest = hashlib.md5(file_bytes).hexdigest()
    safe_name = os.path.basename(filename)
    path = os.path.join(storage_dir, f"{digest}_{safe_name}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path, digest