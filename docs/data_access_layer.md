# Data Access Layer
* A Data Access Layer (DAL) abstracts the complexities of accessing data stored in various locations.
* Those locations can be local or remote e.g. S3 buckets.
* Those locations can be accessed anonymously or might require [credentials](credentials.md).
* S2GOS requires data from heterogeneous datasets, which makes the use of a DAL all the more important.

## Universal Pathlib
* Use of [`universal-pathlib`](https://universal-pathlib.readthedocs.io/en/latest/) package as a DAL.
* Offers a [`pathlib`](https://docs.python.org/3/library/pathlib.html) interface with the capabilities of [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) by introducing the `UPath` class. 
* The `UPath` interface allows the user to open files, make directories, etc.., on various filesystems while abstracting the differences that the filesystems bring.
* `UPath` can access files stored in remote locations that require credentials by storing data those credentials in its `storage_options`.

### Limitations
* Because `UPath` stores credentials, it is not a good candidate for serialization, which is supported by S2GOS config objects.
* For this we also introduce `PathRef`, which works in conjuction with `UPath`.

## `PathRef`
* Serializable representation of a URI with credential ID.
* Simply an object with two fields: `value`, and `cid`.
    - `value`: the URI of the file.
    - `cid`: the credential id, defined by the user or organization.
* Can a generate a `UPath` from it by resolving the `cid` to full credentials (i.e. `storage_options`), that will be passed to the `UPath` along with the `URI`.

![PathRef to UPath Diagram](img/pathref_to_upath.drawio.png)

## To Recap:
* `PathRef` is serializable but cannot be used on its own, it needs to be resolved to a `UPath`.
* A `UPath` can be used for path operations but cannot be serialized.

## See Also:
* [credentials](credentials.md).