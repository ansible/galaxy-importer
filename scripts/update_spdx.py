#!/usr/bin/env python

import json
import requests

# NOTE: This file should be run periodically to update the SPDX licenses.

OUTPUT_PATH = "galaxy_importer/utils/spdx_licenses.json"
SPDX_URL = "https://spdx.org/licenses/licenses.json"

# Fetch licenses from spdx.org.
response = requests.get(SPDX_URL)
result = response.json()

# galaxy-importer only needs the license ID and deprecation status of each license.
licenses = {
    license["licenseId"]: {"deprecated": license["isDeprecatedLicenseId"]}
    for license in result["licenses"]
}

# Write output.
with open(OUTPUT_PATH, "w") as fh:
    json.dump(licenses, fh, indent=4, sort_keys=True)
