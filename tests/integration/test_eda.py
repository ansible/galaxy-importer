import copy
import json
import os
import subprocess


def test_eda_import(workdir, local_image_config):
    assert os.path.exists(workdir)
    url = (
        "https://beta-galaxy.ansible.com/api/v3/plugin/ansible/content/published/"
        + "collections/artifacts/ansible-eda-2.6.0.tar.gz"
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
    assert "aws_sqs_queue.py:main:60: DAR101" in log
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
    results_contents = sorted(results["contents"], key=lambda c: (c["content_type"], c["name"]))
    assert results_contents == sorted(
        [
            {"name": "hello.yml", "content_type": "playbook", "description": None},
            {
                "name": "credential_type_info",
                "content_type": "module",
                "description": "List credential types in EDA Controller",
            },
            {
                "name": "user",
                "content_type": "module",
                "description": "Manage users in EDA controller",
            },
            {
                "name": "rulebook_activation_info",
                "content_type": "module",
                "description": "List rulebook activations in the EDA Controller",
            },
            {
                "name": "rulebook_info",
                "content_type": "module",
                "description": "List all rulebooks",
            },
            {
                "name": "controller_token",
                "content_type": "module",
                "description": "Manage AWX tokens in EDA controller",
            },
            {
                "name": "decision_environment",
                "content_type": "module",
                "description": "Create, update or delete decision environment in EDA Controller",
            },
            {
                "name": "project_info",
                "content_type": "module",
                "description": "List projects in EDA Controller",
            },
            {
                "name": "rulebook_activation",
                "content_type": "module",
                "description": "Manage rulebook activations in the EDA Controller",
            },
            {
                "name": "credential_type",
                "content_type": "module",
                "description": "Manage credential types in EDA Controller",
            },
            {
                "name": "event_stream",
                "content_type": "module",
                "description": "Manage event streams in EDA Controller",
            },
            {
                "name": "event_stream_info",
                "content_type": "module",
                "description": "List event streams in the EDA Controller",
            },
            {
                "name": "credential_info",
                "content_type": "module",
                "description": "List credentials in the EDA Controller",
            },
            {
                "name": "credential",
                "content_type": "module",
                "description": "Manage credentials in EDA Controller",
            },
            {
                "name": "decision_environment_info",
                "content_type": "module",
                "description": "List a decision environment in EDA Controller",
            },
            {
                "name": "project",
                "content_type": "module",
                "description": "Create, update or delete project in EDA Controller",
            },
            {"name": "controller", "content_type": "module_utils", "description": None},
            {"name": "arguments", "content_type": "module_utils", "description": None},
            {"name": "client", "content_type": "module_utils", "description": None},
            {"name": "common", "content_type": "module_utils", "description": None},
            {"name": "errors", "content_type": "module_utils", "description": None},
            {"name": "eda_controller", "content_type": "doc_fragments", "description": None},
            {
                "name": "insert_hosts_to_meta",
                "content_type": "eda/plugins/event_filter",
                "description": (
                    "Extract hosts from the event data and insert them to the meta dict."
                ),
            },
            {
                "name": "dashes_to_underscores",
                "content_type": "eda/plugins/event_filter",
                "description": "Change dashes to underscores.",
            },
            {
                "name": "normalize_keys",
                "content_type": "eda/plugins/event_filter",
                "description": (
                    "Change keys that contain non-alpha numeric or underscore to underscores."
                ),
            },
            {
                "name": "noop",
                "content_type": "eda/plugins/event_filter",
                "description": "Do nothing.",
            },
            {
                "name": "json_filter",
                "content_type": "eda/plugins/event_filter",
                "description": "Filter keys out of events.",
            },
            {
                "name": "webhook",
                "content_type": "eda/plugins/event_source",
                "description": "Receive events via a webhook.",
            },
            {
                "name": "alertmanager",
                "content_type": "eda/plugins/event_source",
                "description": (
                    "Receive events via a webhook from alertmanager or a compatible alerting "
                    "system."
                ),
            },
            {
                "name": "azure_service_bus",
                "content_type": "eda/plugins/event_source",
                "description": "Receive events from an Azure service bus.",
            },
            {
                "name": "range",
                "content_type": "eda/plugins/event_source",
                "description": "Generate events with an increasing index i.",
            },
            {
                "name": "generic",
                "content_type": "eda/plugins/event_source",
                "description": "A generic source plugin that allows you to insert custom data.",
            },
            {
                "name": "url_check",
                "content_type": "eda/plugins/event_source",
                "description": "Poll a set of URLs and sends events with their status.",
            },
            {
                "name": "aws_sqs_queue",
                "content_type": "eda/plugins/event_source",
                "description": "Receive events via an AWS SQS queue.",
            },
            {
                "name": "file",
                "content_type": "eda/plugins/event_source",
                "description": "Load facts from YAML files initially and when the file changes.",
            },
            {
                "name": "pg_listener",
                "content_type": "eda/plugins/event_source",
                "description": "Read events from pg_pub_sub.",
            },
            {
                "name": "kafka",
                "content_type": "eda/plugins/event_source",
                "description": "Receive events via a kafka topic.",
            },
            {
                "name": "journald",
                "content_type": "eda/plugins/event_source",
                "description": "Tail systemd journald logs.",
            },
            {
                "name": "tick",
                "content_type": "eda/plugins/event_source",
                "description": "Generate events with an increasing index i that never ends.",
            },
            {
                "name": "aws_cloudtrail",
                "content_type": "eda/plugins/event_source",
                "description": "Receive events from an AWS CloudTrail",
            },
            {
                "name": "file_watch",
                "content_type": "eda/plugins/event_source",
                "description": "Watch file system changes.",
            },
        ],
        key=lambda c: (c["content_type"], c["name"]),
    )
    assert results["docs_blob"]["contents"] != []
    eda_plugins = [
        c for c in results["docs_blob"]["contents"] if c["content_type"].startswith("eda/")
    ]
    assert len(eda_plugins) == 19
    assert eda_plugins[0]["doc_strings"] != {}
    assert results["docs_blob"]["collection_readme"]["name"] == "README.md"
    assert results["docs_blob"]["collection_readme"]["html"]
    assert results["docs_blob"]["documentation_files"] != []
    assert results["metadata"]["namespace"] == "ansible"
    assert results["metadata"]["name"] == "eda"
    assert results["metadata"]["version"] == "2.6.0"
    assert results["requires_ansible"] == ">=2.15.0"
