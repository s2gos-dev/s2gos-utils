import aiohttp
from dynaconf.utils.boxing import DynaBox
from upath import UPath


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


def to_upath(path_setting: DynaBox | dict | str) -> UPath:
    """
    Generates a UPath from a path object or string.
    Strings will be interpreted as local paths whereas dictionaries will
    forward its components to the UPath constructor.

    Note:
        Protocols that require more than the UPath constructor can provide a
        separate construction function in the `upath_factories` dictionary.

    """
    if isinstance(path_setting, str):
        return UPath(path_setting)

    ps = path_setting.copy()
    if isinstance(path_setting, DynaBox):
        ps = ps.to_dict()

    elif isinstance(ps, dict):
        path = ps.pop("value")

        # Check for specific protocol factories
        protocol = ps.get("protocol", None)
        if protocol in upath_factories:
            return upath_factories[protocol](path, ps)

        # default initialize using existing path and kwargs.
        return UPath(path, **ps)

    else:
        raise NotImplementedError("`path_setting` must either be a `str` or `dict`.")
