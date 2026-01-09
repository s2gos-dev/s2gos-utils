from dynaconf import Dynaconf, Validator
from upath import UPath

from .paths import to_path_ref
from ..io.resolver import resolver


def path(settings=None, validator=None) -> list:
    return []


settings = Dynaconf(
    settings_files=["s2gos_settings.yaml", "s2gos_settings.toml"],
    secrets=".secrets.yaml",
    envvar_prefix="S2GOS",
    validators=[
        Validator(
            "SEARCH_PATHS",
            cast=list,
            default=path,
        ),
    ],
    validate_only="common",
)

def load_config():
    """
    Initialize the resolver with the search paths.
    """
    user_paths = settings.common.search_paths
    for path in user_paths:
        upath = to_path_ref(user_paths).upath
        if upath.exists():
            resolver.append(path)
