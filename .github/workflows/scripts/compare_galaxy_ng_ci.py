import sys

import requests


def main():
    galaxy_ng_url = (
        "https://raw.githubusercontent.com/ansible/galaxy_ng/master/"
        ".ci/scripts/validate_commit_message_custom.py")

    with open(".github/workflows/scripts/check_commits.py") as f:
        galaxy_importer_text = f.read()
    galaxy_ng_text = requests.get(galaxy_ng_url).text

    if galaxy_importer_text == galaxy_ng_text:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
