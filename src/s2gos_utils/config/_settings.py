from dynaconf import Dynaconf, Validator


def path(settings=None, validator=None) -> list:
    return []

settings = Dynaconf(
    settings_files=["s2gos_settings.toml"],
    envvar_prefix="S2GOS",
    validate_on_update=True,
    validators=[
        Validator(
            "DATA_PATH",
            cast=list,
            default=path,
        ),
    ],
)
