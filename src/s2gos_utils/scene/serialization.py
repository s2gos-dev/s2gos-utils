import os
from pathlib import Path
from typing import Optional, Union


def serialize_path(path: Union[Path, str, None]) -> Optional[str]:
    """Serialize Path object to string using __fspath__ protocol.

    Args:
        path: Path object to serialize

    Returns:
        String representation of path or None if input is None
    """
    if path is None:
        return None
    return os.fspath(path)


def deserialize_path(path_str: Optional[str]) -> Optional[Path]:
    """Deserialize string to Path object.

    Args:
        path_str: String representation of path

    Returns:
        Path object or None if input is None
    """
    if path_str is None:
        return None
    return Path(path_str)
