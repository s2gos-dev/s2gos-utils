# import os
import os
from typing import Annotated, Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from upath import UPath


class UPathType:
    """Custom Pydantic type for UPath that provides core schema."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Define how Pydantic should validate and serialize UPath."""
        schema = handler(os.PathLike)
        return core_schema.no_info_after_validator_function(
            cls.validate,
            schema,
        )

    @staticmethod
    def validate(value: Any) -> UPath:
        """Convert string/Path to UPath."""
        if isinstance(value, UPath):
            return value
        return UPath(value)


#: Path-like type annotation for all path parameters
#: Supports local paths, remote URLs, and UPath objects
PathLike = Annotated[UPath, UPathType()]
