from dynaconf import Dynaconf, Validator


def path(settings=None, validator=None) -> list:
    return []


settings = Dynaconf(
    settings_files=["s2gos_settings.toml"],
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
