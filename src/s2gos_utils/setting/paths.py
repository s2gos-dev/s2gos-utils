import warnings

import aiohttp
from dynaconf.utils.boxing import Box, DynaBox
from upath import UPath

from ..io.resolver import resolver
from ..typing import PathRef


def to_https_upath(path: str, ps: dict) -> UPath:
    # use HTTP Basic Auth
    username = ps.pop("username") if "username" in ps else ""
    password = ps.pop("password") if "password" in ps else ""
    auth = aiohttp.BasicAuth(username, password)

    return UPath(path, client_kwargs={"auth": auth}, **ps)


# UPath factory from settings.
# keys: str = <protocol name>
# value: Callable = <construction function>, signature (path : str, ps : dict) -> UPath
upath_factories = {
    "https": to_https_upath,
}

def to_path_ref(path_setting: DynaBox | dict | str) -> PathRef:
    if isinstance(path_setting, str):
        # Simple string path
        return PathRef(str(path_setting))
    
    ps = path_setting.copy()
    if isinstance(path_setting, (DynaBox, Box)):
        ps = ps.to_dict()

    if isinstance(ps, dict):
        return PathRef(**ps)


def to_upath(path_setting: DynaBox | dict | str) -> PathRef:
    """
    Convert path setting to PathRef.

    Supports three formats:
    1. String: simple path (no credentials)
    2. Dict with credential_id: path with credential reference (new format)
    3. Dict with direct credentials: legacy format (deprecated)

    Args:
        path_setting: Path configuration (string, dict, or DynaBox)

    Returns:
        PathRef object

    Examples:
        # Simple string path
        to_upath("/local/path")

        # Path with credential reference (new format)
        to_upath({"value": "https://example.com/data", "credential_id": "mycred"})

        # Legacy format with direct credentials (deprecated)
        to_upath({"value": "https://example.com/data", "username": "user", "password": "pass"})
    """
    if isinstance(path_setting, str):
        # Simple string path - resolve and return
        resolved = resolver.resolve(UPath(path_setting))
        return PathRef(value=str(resolved))

    ps = path_setting.copy()
    if isinstance(path_setting, (DynaBox, Box)):
        ps = ps.to_dict()

    if isinstance(ps, dict):
        path = ps.pop("value")
        credential_id = ps.pop("credential_id", None)

        if credential_id:
            # New format: credential reference
            return PathRef(value=path, credential_id=credential_id)

        # Legacy format: direct credentials (backward compatibility)
        if "username" in ps or "key" in ps:
            warnings.warn(
                "Direct credentials in config are deprecated. "
                "Use credential_id and store credentials in .secrets.yaml or environment variables. "
                "See documentation for migration guide.",
                DeprecationWarning,
                stacklevel=2,
            )
            # For backward compatibility, still construct the UPath with credentials
            # but return as PathRef without credential_id
            protocol = ps.get("protocol", None)
            if protocol in upath_factories:
                upath = upath_factories[protocol](path, ps)
            else:
                upath = UPath(path, **ps)
            # Return as PathRef (but credentials won't be preserved in serialization)
            return PathRef(value=str(upath))

        # No credentials - simple path
        resolved = resolver.resolve(UPath(path, **ps))
        return PathRef(value=str(resolved))

    else:
        raise NotImplementedError("`path_setting` must either be a `str` or `dict`.")
