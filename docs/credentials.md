# Credentials
* Credentials and secrets are required to access files and datasets stored in remote locations.
* Secrets should never appear in version control or in serialized files.
* For this reason, S2GOS uses credential IDs and credential providers.

## Credential ID
* Used by credential provider to identify credentials linked to a remote path.
* Use descriptive names that indicate the purpose or data source
* Examples: earthdatahub, s3ovh, my_institution, landsat_archive

## Supported Authentication Method

### BasicAuth
* `username`
* `password`

### S3
* `key`
* `secret`
* `endpoint_url`

## Supported Credential Providers

### Environment
* Reads credentials directly from Environment Variables.
* Should be of the form S2GOS_CREDENTIALS__<crendential_id>__<variable>
* BasicAuth Example:
    - S2GOS_CREDENTIALS__earthdatahub__TYPE=basic_auth
    - S2GOS_CREDENTIALS__earthdatahub__USERNAME=...
    - S2GOS_CREDENTIALS__earthdatahub__PASSWORD=...
* S3 Example:
    - S2GOS_CREDENTIALS__s3bucket__TYPE=s3
    - S2GOS_CREDENTIALS__s3bucket__KEY=...
    - S2GOS_CREDENTIALS__s3bucket__SECRET=...
    - S2GOS_CREDENTIALS__s3bucket__ENDPOINT_URL=...

### Dynaconf
* Reads credentials from .secret.yaml.
* This file is gitignored, never commit it to version control.
* Note that Environment variables take precedence over .secrets.yaml
* See the [dynaconf documentation](https://www.dynaconf.com/secrets/) for more details on how secrets are handled. 
* Template example:

```yaml
# S2GOS Credentials Template
#
credentials:
  # Example: HTTP Basic Authentication
  # Used for HTTPS data sources that require username/password
  earthdatahub:
    type: basic_auth
    username: your_username_here
    password: your_password_or_token_here

  # Example: S3 credentials
  # Used for S3 or S3-compatible object storage
  s3ovh:
    type: s3
    key: your_access_key_here
    secret: your_secret_key_here
    # Optional: endpoint URL for S3-compatible services (not needed for AWS S3)
    endpoint_url: https://s3.de.io.cloud.ovh.net

  # Add your own credentials below
  # my_custom_source:
  #   type: basic_auth
  #   username: my_user
  #   password: my_password
```

## See Also:
* [Data Access Layer](data_access_layer.md).