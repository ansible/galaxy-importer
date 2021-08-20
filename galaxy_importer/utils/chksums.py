import logging
import os

import hashlib

from galaxy_importer import exceptions as exc

log = logging.getLogger(__name__)


def sha256sum_from_fo(fo):
    block_size = 65536
    sha256 = hashlib.sha256()
    for block in iter(lambda: fo.read(block_size), b""):
        sha256.update(block)
    return sha256.hexdigest()


def sha256sum_from_path(filename):
    with open(filename, "rb") as fo:
        return sha256sum_from_fo(fo)


def check_artifact_file(path_prefix, artifact_file):
    """Check existences of artifact_file on fs and check the chksum matches

    Args:
        path_prefix (str): Any file path prefix we need to add to file paths in the
            CollectionArtifactFile artifact_file
        artifact_file (CollectionArtifactFile): object with the expected info about
            the file on the fs that will be checked.
            This info includes name, type, path, and checksum.

    Raises:
        CollectionArtifactFileNotFound: If artifact_file is not found on the file system.
        CollectionArtifactFileChecksumError: If the sha256sum of the on disk
            artifact_file contents does not match artifact_file.chksum_sha256.

    Returns:
        bool: True if artifact_file check is ok, otherwise should raise exception
    """
    log.debug("artifact_file: %s", artifact_file)

    artifact_file_path = os.path.join(path_prefix, artifact_file.name)
    if not os.path.exists(artifact_file_path):
        msg = f"The file ({artifact_file.name}) was not found"
        raise exc.CollectionArtifactFileNotFound(missing_file=artifact_file.name, msg=msg)

    actual_chksum = sha256sum_from_path(artifact_file_path)

    if actual_chksum != artifact_file.chksum_sha256:
        err_msg = (
            f"File {artifact_file.name} sha256sum should be "
            f"{artifact_file.chksum_sha256} but the actual sha256sum was {actual_chksum}"
        )
        log.error(err_msg)
        raise exc.CollectionArtifactFileChecksumError(err_msg)

    return True
