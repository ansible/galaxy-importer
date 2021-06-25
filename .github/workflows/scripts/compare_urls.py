import os
import sys

import requests


def main():
    url_1 = os.environ["URL_1"]
    url_2 = os.environ["URL_2"]

    do_contents_match = requests.get(url_1).text == requests.get(url_2).text

    if do_contents_match:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
