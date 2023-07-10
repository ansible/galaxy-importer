import atexit
import os
import shutil
import subprocess
import tempfile

import pytest


def clean_files(path):
    shutil.rmtree(path)


@pytest.fixture
def workdir():
    tdir = tempfile.mkdtemp()
    atexit.register(clean_files, tdir)
    return tdir


@pytest.fixture
def local_image_config():
    config = [
        "[galaxy-importer]",
        "RUN_ANSIBLE_TEST=True",
        "ANSIBLE_TEST_LOCAL_IMAGE=True",
        "LOCAL_IMAGE_DOCKER=True",
    ]
    config = "\n".join(config)

    tdir = tempfile.mkdtemp()
    atexit.register(clean_files, tdir)

    config_path = os.path.join(tdir, "galaxy-importer.cfg")
    with open(config_path, "w") as f:
        f.write(config)

    return {"GALAXY_IMPORTER_CONFIG": config_path}


@pytest.fixture
def simple_artifact():
    tdir = tempfile.mkdtemp()
    atexit.register(clean_files, tdir)

    cmd = "ansible-galaxy collection init foo.bar"
    pid = subprocess.run(
        cmd, shell=True, cwd=tdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout

    coldir = os.path.join(tdir, "foo", "bar")
    metadir = os.path.join(coldir, "meta")

    if not os.path.exists(metadir):
        os.makedirs(metadir)
    with open(os.path.join(metadir, "runtime.yml"), "w") as f:
        f.write("requires_ansible: '>=2.9.10,<2.11.5'\n")

    cmd = "ansible-galaxy collection build ."
    pid = subprocess.run(
        cmd, shell=True, cwd=coldir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    lines = pid.stdout.decode("utf-8").split("\n")
    tarball = None
    for line in lines:
        line = line.strip()
        if not line or not line.endswith(".tar.gz"):
            continue
        tarball = line.split()[-1]
    assert tarball, lines
    return tarball


@pytest.fixture
def simple_legacy_role():
    tdir = tempfile.mkdtemp()
    atexit.register(clean_files, tdir)

    cmd = "ansible-galaxy role init bar_role"
    pid = subprocess.run(
        cmd, shell=True, cwd=tdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout
    return os.path.join(tdir, "bar_role")
