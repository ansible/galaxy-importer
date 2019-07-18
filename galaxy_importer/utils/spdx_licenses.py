import json
import logging

from pkg_resources import resource_filename


log = logging.getLogger(__name__)

# use _get_spdx() to ref the spdx_license info, so it
# only loaded from disk once
_SPDX_LICENSES = None


def _load_spdx():
    license_path = resource_filename(__name__, 'spdx_licenses.json')
    try:
        with open(license_path, 'r') as fo:
            return json.load(fo)
    except EnvironmentError as exc:
        log.warning('Unable to open %s to load the list of acceptable '
                    'open source licenses: %s', license_path, exc)
        log.exception(exc)
        return {}


def _get_spdx():
    global _SPDX_LICENSES

    if not _SPDX_LICENSES:
        _SPDX_LICENSES = _load_spdx()

    return _SPDX_LICENSES


def is_valid_license_id(license_id):
    """Check if license_id is valid and non-deprecated SPDX ID."""
    if license_id is None:
        return False

    valid_license_ids = _get_spdx()
    valid = valid_license_ids.get(license_id, None)
    if valid is None:
        return False

    # license was in list, but is deprecated
    if valid and valid.get('deprecated', None):
        return False

    return True
