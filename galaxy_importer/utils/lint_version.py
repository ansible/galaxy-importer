from importlib.metadata import version, PackageNotFoundError


def get_version_from_metadata(package_name):
    """Uses importlib.metadata.version to retrieve package version"""
    try:
        return version(package_name)
    except PackageNotFoundError:
        return ""
