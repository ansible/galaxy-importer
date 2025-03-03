import copy
import json
import os
import subprocess


def test_eda_import(workdir, local_image_config):
    assert os.path.exists(workdir)
    url = (
        "https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/"
        + "collections/artifacts/ansible-eda-1.4.2.tar.gz"
    )
    dst = os.path.join(workdir, os.path.basename(url))
    pid = subprocess.run(f"curl -L -o {dst} {url}", shell=True)
    assert pid.returncode == 0
    assert os.path.exists(dst)

    env = copy.deepcopy(dict(os.environ))
    env.update(local_image_config)

    cmd = f"python3 -m galaxy_importer.main {dst}"
    pid = subprocess.run(
        cmd, shell=True, cwd=workdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout

    # the log should contain all the relevant messages
    log = pid.stdout.decode("utf-8")
    assert "Running ansible-test sanity on" in log
    assert "Running sanity test" in log
    assert "ansible-test sanity complete." in log

    # EDA specific messages ...
    assert "EDA plugin content found. Running ruff on /extensions/eda/plugins..." in log
    # No errors in log to verify ruff ran
    assert "Running darglint on /extensions/eda/plugins..." in log
    assert "aws_sqs_queue.py:main:33: DAR101" in log
    assert "Running pylint on /extensions/eda/plugins/event_source..." in log
    assert "Running pylint on /extensions/eda/plugins/event_filter..." in log
    assert "EDA linting complete." in log

    assert "Removing temporary files, image and container" in log
    assert "Importer processing completed successfully" in log

    # it should have stored structured data in the pwd
    results_file = os.path.join(workdir, "importer_result.json")
    assert os.path.exists(results_file)
    with open(results_file) as f:
        results = json.loads(f.read())

    # the data should have all the relevant bits
    assert results["contents"] == [
        {
            "content_type": "module",
            "description": "Upper cases a passed in string",
            "name": "upcase",
        },
        {"content_type": "playbook", "description": None, "name": "hello.yml"},
        {"content_type": "role", "description": "your role description", "name": "test_role"},
    ]
    assert results["docs_blob"]["contents"] != []
    assert results["docs_blob"]["collection_readme"]["name"] == "README.md"
    assert results["docs_blob"]["collection_readme"]["html"]
    assert results["docs_blob"]["documentation_files"] == []
    assert results["metadata"]["namespace"] == "ansible"
    assert results["metadata"]["name"] == "eda"
    assert results["metadata"]["version"] == "1.4.2"
    assert results["requires_ansible"] == ">=2.9.10"
