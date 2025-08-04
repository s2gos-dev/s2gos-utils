import os
from typing import Union

from upath import UPath

#: Path-like type annotation for all path parameters
#: Supports local paths, remote URLs, and UPath objects
PathLike = Union[str, bytes, os.PathLike, UPath]
