# import os
import pathlib
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, GetCoreSchemaHandler, model_validator
from pydantic_core import core_schema
from upath import UPath


class UPathType:
    """Custom Pydantic type for UPath that provides core schema."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Define how Pydantic should validate and serialize UPath."""
        # Accept UPath + subclasses
        upath_schema = core_schema.is_instance_schema(UPath)

        # Accept strings and pathlib.Path
        str_schema = core_schema.str_schema()
        path_schema = core_schema.is_instance_schema(pathlib.Path)

        union_schema = core_schema.union_schema([upath_schema, path_schema, str_schema])
        return core_schema.no_info_after_validator_function(
            cls.validate,
            union_schema,
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


# TODO: might need to be relocated to paths.py
# also completely removes the need for UPathType now.
class PathRef(BaseModel):
    """
    Path configuration that preserves credential reference through serialization.

    This model allows paths to reference credentials by ID rather than embedding
    actual credentials. When serialized to JSON, only the path value and credential_id
    are stored (no actual credentials). When deserialized, credentials are resolved
    from the credential provider (environment variables or .secrets.yaml).

    Attributes:
        value: The actual path/URL
        cid: Optional reference to a credential in the credential provider

    Example:
        # With credentials
        path = PathRef(
            path="https://data.earthdatahub.destine.eu/data.zarr",
            cid="earthdatahub"
        )

        # Without credentials (public or local path)
        path = PathRef(path="/local/path/data.zarr")

        # Access the authenticated UPath
        upath = path.upath
    """

    value: str = Field(description="value")
    cid: str | None = Field(default=None, description="Credential ID")

    def __init__(self, value, cid=None, **kwargs):
        value = str(value) if isinstance(value, UPath) else value
        super(PathRef, self).__init__(
            value=value, cid=cid, **kwargs
        )

    @model_validator(mode="before")
    @classmethod
    def convert_to_pathref(cls, value):
        if isinstance(value, str):
            return {"value": value}
        
        elif isinstance(value, UPath):
            cid = value.storage_options.get("cid")
            return {"value": str(value), "cid":cid}
        
        return value

    @property
    def upath(self) -> UPath:
        """
        Get the authenticated UPath by resolving credentials.

        If `cid` is set, retrieves the credential from the credential
        provider and constructs an authenticated UPath. Otherwise returns a
        simple UPath without authentication.

        Returns:
            UPath object with authentication if `cid` is set

        Raises:
            ValueError: If `cid` is set but credential is not found
        """
        if self.cid:
            from s2gos_utils.setting.credentials import get_credential

            cred = get_credential(self.cid)
            if not cred:
                raise ValueError(
                    f"Credential '{self.cid}' not found. "
                    f"Set S2GOS_CRED_{self.cid}_* environment variables "
                    f"or add to .secrets.yaml"
                )
            kwargs = cred.upath_kwargs
            return UPath(self.value, **kwargs)
        else:
            # No credentials needed (local path or public URL)
            return UPath(self.value)

    def __str__(self) -> str:
        """Return the path value as a string"""
        return self.value

    model_config = {"arbitrary_types_allowed": True}
