import json
from typing import Any, BinaryIO, Dict, Optional, TextIO, Union

import geopandas as gpd
import pandas as pd
import xarray as xr
import yaml
from upath import UPath

from ..typing import PathLike, PathRef


def to_upath(path: PathLike | PathRef) -> UPath:
    if isinstance(path, PathRef):
        return path.upath
    else:
        return UPath(path)


def open_file(
    path: PathLike | PathRef, mode: str = "r", **kwargs
) -> Union[TextIO, BinaryIO]:
    """Open a file using UPath for unified access across storage backends.

    Args:
        path: Path to file (local or remote).
        mode: File mode ('r', 'rb', 'w', 'wb', etc.).
        **kwargs: Additional arguments for UPath.open().

    Returns:
        A file object.
    """
    return to_upath(path).open(mode=mode, **kwargs)


def read_feather(path: PathLike, **kwargs) -> pd.DataFrame:
    """Read a feather file from any backend supported by fsspec.

    Args:
        path: Path to the feather file.
        **kwargs: Additional arguments for pd.read_feather().

    Returns:
        A pandas DataFrame.
    """
    with open_file(path, "rb") as f:
        return pd.read_feather(f, **kwargs)


def read_geofeather(path: PathLike, **kwargs) -> gpd.GeoDataFrame:
    """Read a GeoFeather file as a GeoDataFrame from any backend.

    Args:
        path: Path to the feather file.
        **kwargs: Additional arguments for gpd.read_feather().

    Returns:
        A GeoDataFrame.
    """
    with open_file(path, "rb") as f:
        return gpd.read_feather(f, **kwargs)


def read_json(path: PathLike, **kwargs) -> Dict[str, Any]:
    """Read a JSON file from any backend supported by fsspec.

    Args:
        path: Path to the JSON file.
        **kwargs: Additional arguments for json.load().

    Returns:
        A dictionary with the JSON content.
    """
    with open_file(path, "r") as f:
        return json.load(f, **kwargs)


def read_yaml(path: PathLike, **kwargs) -> Dict[str, Any]:
    """Read a YAML file from any backend supported by fsspec.

    Args:
        path: Path to the YAML file.
        **kwargs: Additional arguments for yaml.safe_load().

    Returns:
        A dictionary with the YAML content.
    """
    with open_file(path, "r") as f:
        return yaml.safe_load(f, **kwargs)


def open_dataarray(path: PathRef | PathLike, **kwargs) -> xr.DataArray:
    """Open an xarray DataArray, letting xarray handle the fsspec backend.

    Args:
        path: Path to the data file.
        **kwargs: Additional arguments for xr.open_dataarray().

    Returns:
        An xarray DataArray.
    """
    path = to_upath(path)
    mapper = expand_mapper(path)
    return xr.open_dataarray(mapper, **kwargs)


def open_dataset(
    path: UPath | PathRef,
    engine: str | None = None,
    fsspec_caching: dict | None = None,
    **kwargs,
):
    """
    Open an xarray Dataset. 
    Uses `universal_pathlib` (`UPath`) to handle remote location access by 
    passing the `storage_options` when relevant and uses `fsspec` to handle by
    opening using the `FileSystem.open` method directly.
    Note that the `netcdf4` engine can only use a local caching strategy. In such
    cases, `fsspec_caching` is passed to the `simplecache` argument of 
    `fsspec.open_local`.

    Args:
        path: Path to the data file.
        engine: The backend engine used by xarray.
        fsspec_caching: 
            Kwargs arguments for fsspec caching. for engine="netcdf4", 
            this is passed to `simplecache`.
        **kwargs: Additional arguments for xr.open_dataset().

    Returns:
        An xarray Dataset.
    """
    path = to_upath(path)

    # Will trigger an helpful assert if it cannot find the proper engine, which
    # gets obfuscated by the storage option exception otherwise.
    if engine is None:
        engine = xr.backends.plugins.guess_engine(path.path)

    # Check for storage options for authentication
    if len(path.storage_options) > 0 and "storage_options" not in kwargs:
        kwargs["storage_options"] = path.storage_options

    if fsspec_caching is not None:
        fs = path.fs
        if engine == "netcdf4":
            import fsspec

            return xr.open_dataset(
                fsspec.open_local(
                    f"simplecache::{str(path)}", simplecache=fsspec_caching
                ),
                engine=engine,
                **kwargs,
            )
        else:
            return xr.open_dataset(
                fs.open(str(path), **fsspec_caching), engine=engine, **kwargs
            )

    return xr.open_dataset(str(path), engine=engine, **kwargs)


def is_remote_path(path: PathLike) -> bool:
    """Check if a path is a remote URL using UPath protocol detection."""
    return to_upath(path).protocol != "file"


def is_absolute_path(path: PathLike) -> bool:
    """Check if a path is absolute (works for both local and remote paths)."""
    upath = to_upath(path)
    return upath.protocol != "file" or upath.is_absolute()


def exists(path: PathLike) -> bool:
    """Check if path exists (local or remote) using UPath."""
    return to_upath(path).exists()


def mkdir(
    path: PathLike, parents: bool = True, exist_ok: bool = True, **kwargs
) -> None:
    """Create directory using UPath (supports local and some remote protocols)."""
    to_upath(path).mkdir(parents=parents, exist_ok=exist_ok, **kwargs)


def copy(src: PathLike | PathRef, dst: PathLike | PathRef, **kwargs) -> None:
    """Create directory using UPath (supports local and some remote protocols)."""
    to_upath(src).copy(to_upath(dst), **kwargs)


def optional_str(path: Optional[PathLike]) -> Optional[str]:
    """Convert a path-like object to a string, handling None elegantly."""
    return str(path) if path is not None else None


def normalize_path(path: PathLike) -> str:
    """Normalize a path using UPath for consistent handling.

    Always returns a string for configuration compatibility.
    """
    return str(to_upath(path))


def expand_mapper(path: UPath):
    """Expands a UPath to a FSMapper."""
    return path.fs.get_mapper(path.path)
