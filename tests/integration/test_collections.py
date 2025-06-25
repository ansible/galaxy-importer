import copy
import json
import os
import subprocess


def test_collection_community_general_import(workdir, local_fast_config):
    assert os.path.exists(workdir)
    url = (
        "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/"
        + "collections/artifacts/community-general-8.2.0.tar.gz"
    )
    dst = os.path.join(workdir, os.path.basename(url))
    pid = subprocess.run(f"curl -L -o {dst} {url}", shell=True)
    assert pid.returncode == 0
    assert os.path.exists(dst)

    env = copy.deepcopy(dict(os.environ))
    env.update(local_fast_config)

    cmd = f"python3 -m galaxy_importer.main {dst}"
    pid = subprocess.run(
        cmd, shell=True, cwd=workdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout

    # the log should contain all the relevant messages
    log = pid.stdout.decode("utf-8")

    # should have no errors
    assert "error" not in log.lower()

    # should have skipped ansible-test
    assert "skip ansible-test sanity test" in log

    # check for success message
    assert "Importer processing completed successfully" in log

    # it should have stored structured data in the pwd
    results_file = os.path.join(workdir, "importer_result.json")
    assert os.path.exists(results_file)
    with open(results_file) as f:
        results = json.loads(f.read())

    # the data should have all the relevant bits
    assert results["metadata"]["namespace"] == "community"
    assert results["metadata"]["name"] == "general"
    assert results["metadata"]["version"] == "8.2.0"
    assert results["requires_ansible"] == ">=2.13.0"

    # make sure it found all the files
    contents = {(x["content_type"], x["name"]): x for x in results["contents"]}
    assert len(contents.keys()) == 842

    # check a small sample
    assert ("test", "a_module") in contents
    assert ("module_utils", "version") in contents
    assert ("module", "xfconf") in contents
    assert ("module", "jabber") in contents
    assert ("filter", "time") in contents
    assert ("doc_fragments", "nomad") in contents
    assert ("connection", "lxc") in contents
    assert ("callback", "yaml") in contents
    assert ("cache", "yaml") in contents
    assert ("become", "pbrun") in contents
    assert ("action", "shutdown") in contents

    # make sure it found all the docs
    docs_contents = {
        (x["content_type"], x["content_name"]): x for x in results["docs_blob"]["contents"]
    }
    assert len(docs_contents.keys()) == 842

    # check a small sample
    assert ("test", "a_module") in docs_contents
    assert ("module_utils", "version") in docs_contents
    assert ("module", "xfconf") in docs_contents
    assert ("module", "jabber") in docs_contents
    assert ("filter", "time") in docs_contents
    assert ("doc_fragments", "nomad") in docs_contents
    assert ("connection", "lxc") in docs_contents
    assert ("callback", "yaml") in docs_contents
    assert ("cache", "yaml") in docs_contents
    assert ("become", "pbrun") in docs_contents
    assert ("action", "shutdown") in docs_contents


def test_collection_with_patterns_import(workdir, local_fast_config):
    assert os.path.exists(workdir)
    url = (
        "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/"
        + "collections/artifacts/jerabekjiri-sample_collection_with_pattern-1.0.0.tar.gz"
    )
    dst = os.path.join(workdir, os.path.basename(url))
    pid = subprocess.run(f"curl -L -o {dst} {url}", shell=True)

    assert pid.returncode == 0
    assert os.path.exists(dst)

    env = copy.deepcopy(dict(os.environ))
    env.update(local_fast_config)

    cmd = f"python3 -m galaxy_importer.main {dst}"
    pid = subprocess.run(
        cmd, shell=True, cwd=workdir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout

    # the log should contain all the relevant messages
    log = pid.stdout.decode("utf-8")

    # should have no errors
    assert "error" not in log.lower()

    assert "extensions/patterns/sample_pattern/templates not found, skipping" in log
    assert (
        "Successfully loaded extensions/patterns/sample_pattern/meta/pattern.json/pattern.json"
        in log
    )

    # verify patterns log
    content_types_with_path = [
        ("patterns", "patterns.sample_pattern.README.md"),
        (
            "patterns/execution-environments",
            "patterns.sample_pattern.execution_environments.execution_environment.yml",
        ),
        ("patterns/meta", "patterns.sample_pattern.meta.pattern.json"),
        ("patterns/playbooks", "patterns.sample_pattern.playbooks.group_vars.all.yml"),
        ("patterns/playbooks", "patterns.sample_pattern.playbooks.site.yml"),
    ]

    for content_type, content_path in content_types_with_path:
        assert f"Loading {content_type} {content_path}" in log

    # check for success message
    assert "Importer processing completed successfully" in log

    # it should have stored structured data in the pwd
    results_file = os.path.join(workdir, "importer_result.json")
    assert os.path.exists(results_file)
    with open(results_file) as f:
        results = json.loads(f.read())

    # for content in results["contents"]:
    for content_type, content_path in content_types_with_path:
        assert {
            "name": content_path,
            "content_type": content_type,
            "description": None,
        } in results["contents"]

    # verify patterns metadata
    patterns = results["patterns"]
    assert len(patterns) == 1

    pattern = patterns[0]
    assert "name" in pattern
    assert "description" in pattern
    assert "short_description" in pattern
    assert "tags" in pattern
    assert "aap_resources" in pattern

    assert "controller_project" in pattern["aap_resources"]
    assert "controller_execution_environment" in pattern["aap_resources"]
    assert "controller_labels" in pattern["aap_resources"]
    assert "controller_job_templates" in pattern["aap_resources"]
