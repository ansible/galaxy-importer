import copy
import json
import os
import subprocess


def test_local_build_container_with_collection(workdir, local_image_config, simple_artifact):
    # use the parent env to preserve venv vars
    env = copy.deepcopy(dict(os.environ))
    env.update(local_image_config)

    # this relies on the GALAXY_IMPORTER_CONFIG to know where to find the config
    # it should also spawn an image build and use that image for the ansible-test phase
    cmd = f"python3 -m galaxy_importer.main {simple_artifact}"
    pid = subprocess.run(
        cmd, shell=True, cwd=workdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        #cmd, shell=True, cwd=workdir, env=env
    )
    import epdb; epdb.st()
    assert pid.returncode == 0, pid.stdout

    # the log should contain all the relevant messages
    log = pid.stdout.decode("utf-8")
    assert "Running ansible-test sanity on" in log
    assert "Running sanity test" in log
    assert "ansible-test sanity complete." in log
    assert "No EDA content found. Skipping linters." in log
    assert "Removing temporary files, image and container" in log
    assert "Importer processing completed successfully" in log

    # it should have stored structured data in the pwd
    results_file = os.path.join(workdir, "importer_result.json")
    assert os.path.exists(results_file)
    with open(results_file, "r") as f:
        results = json.loads(f.read())

    # the data should have all the relevant bits
    assert results["contents"] == []
    assert results["docs_blob"]["contents"] == []
    assert results["docs_blob"]["collection_readme"]["name"] == "README.md"
    assert results["docs_blob"]["collection_readme"]["html"]
    assert results["docs_blob"]["documentation_files"] == []
    assert results["metadata"]["namespace"] == "foo"
    assert results["metadata"]["name"] == "bar"
    assert results["metadata"]["version"] == "1.0.0"
    assert results["requires_ansible"] == ">=2.9.10,<2.11.5"


def test_local_build_container_with_legacy_role(local_image_config, simple_legacy_role):
    # use the parent env to preserve venv vars
    env = copy.deepcopy(dict(os.environ))
    env.update(local_image_config)

    # this relies on the GALAXY_IMPORTER_CONFIG to know where to find the config
    # it should also spawn an image build and use that image for the ansible-test phase
    cmd = (
        f"python3 -m galaxy_importer.main {simple_legacy_role}"
        + " --legacy-role --namespace foo-namespace"
    )
    workdir = os.path.dirname(simple_legacy_role)
    pid = subprocess.run(
        cmd, shell=True, cwd=workdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout

    # the log should contain all the relevant messages
    log = pid.stdout.decode("utf-8")

    assert "Determined role name to be bar_role" in log
    assert "Linting role bar_role via ansible-lint..." in log
    assert "Should change default metadata: author" in log
    assert "Should change default metadata: company" in log
    assert "Should change default metadata: license" in log
    assert "Role info should contain platforms" in log
    assert "All plays should be named." in log
    assert "...ansible-lint run complete" in log
    assert "Legacy role loading complete" in log

    # it should have stored structured data in the pwd
    results_file = os.path.join(workdir, "importer_result.json")
    assert os.path.exists(results_file)
    with open(results_file, "r") as f:
        results = json.loads(f.read())

    # the data should have all the relevant bits
    assert results["metadata"]["dependencies"] == []
    assert results["metadata"]["galaxy_info"]["author"] == "your name"
    assert results["metadata"]["galaxy_info"]["description"] == "your role description"
    assert results["metadata"]["galaxy_info"]["role_name"] is None
    assert results["name"] == "bar_role"
    assert results["namespace"] == "foo-namespace"
    assert results["readme_html"]
