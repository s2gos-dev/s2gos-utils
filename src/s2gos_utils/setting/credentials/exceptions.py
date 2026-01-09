class CredentialNotFoundError(Exception):
    """
    Raised when a credential ID cannot be found in any provider.
    Indicates the credential is not configured at all.
    """
    def __init__(self, credential_id: str):
        self.credential_id = credential_id
        message = (
            f"Credential '{credential_id}' not found in provider. "
            f"To configure:\n"
            f"  - Environment: S2GOS_CRED_{credential_id}_TYPE, "
            f"S2GOS_CRED_{credential_id}_USERNAME, etc.\n"
            f"  - Or add to .secrets.yaml under 'credentials.{credential_id}'"
        )
        super().__init__(message)

class CredentialValidationError(Exception):
    """
    Raised when a credential exists but is malformed or invalid.
    Indicates the credential is configured but has missing/invalid fields.
    """
    def __init__(
        self,
        credential_id: str,
        message: str,
        provider: str = None,
        missing_fields: list[str] = None
    ):
        self.credential_id = credential_id
        self.provider = provider
        self.missing_fields = missing_fields or []

        provider_str = f" in {provider}" if provider else ""
        error_msg = f"Credential '{credential_id}'{provider_str}: {message}"

        if missing_fields:
            fields_str = ", ".join(missing_fields)
            error_msg += f"\nMissing required fields: {fields_str}"

        super().__init__(error_msg)