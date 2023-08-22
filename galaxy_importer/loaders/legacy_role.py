import logging
import os
import shutil
from subprocess import PIPE, Popen, TimeoutExpired

from galaxy_importer import config
from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer.utils import markup
from galaxy_importer import schema

default_logger = logging.getLogger(__name__)


class LegacyRoleLoader(object):
    """Loads legacy role information."""

    def __init__(self, dirname, namespace, cfg=None, logger=None):
        self.dirname = dirname
        self.namespace = namespace

        # If no config is found, use default configuration values.
        self.cfg = cfg
        if self.cfg is None:
            config_data = config.ConfigFile.load()
            self.cfg = config.Config(config_data=config_data)

        self.log = logger or default_logger

        self.name = None
        self.metadata = None
        self.content_obj = None
        self.readme = None
        self.readme_html = None

    def load(self):
        """Loads role metadata and content information and lints role."""

        self._validate_namespace()

        self.metadata = self._load_metadata()
        self.name = self._load_name()
        self.readme = self._load_readme()
        self.readme_html = markup.get_html(self.readme)

        if self.cfg.run_ansible_lint:
            self._lint_role()

        return schema.LegacyImportResult(
            namespace=self.namespace,
            name=self.name,
            metadata=self.metadata,
            readme_file=self.readme.name,
            readme_html=self.readme_html,
        )

    def _validate_namespace(self):
        """Validate the namespace is a valid github username."""

        if constants.GITHUB_USERNAME_REGEXP.match(self.namespace) is None:
            raise exc.ImporterError(f"namespace {self.namespace} is invalid")

    def _load_metadata(self):
        """Loads role metadata."""

        # Search for metadata in paths
        # meta.yml, meta.yaml, meta/main.yml, and meta/main.yaml.
        meta_path = None
        for file in constants.ROLE_META_FILES:
            path = os.path.join(self.dirname, file)
            if os.path.exists(path):
                meta_path = path
                break
        if meta_path is None:
            raise exc.ImporterError("Metadata not found at any path")

        return schema.LegacyMetadata.parse(meta_path)

    def _load_name(self):
        """Determine the name of a legacy role."""

        # The name of the role is determined by the name of its directory
        # UNLESS there is a galaxy_info.role_name field. The metadata field
        # overrides the directory name.
        if self.metadata.galaxy_info.role_name is not None:
            name = self.metadata.galaxy_info.role_name
        else:
            name = os.path.basename(os.path.normpath(self.dirname))

        self.log.info(f"Determined role name to be {name}")

        return name

    def _load_readme(self):
        """Find the README file of a role."""

        readme = markup.get_readme_doc_file(self.dirname)
        if not readme:
            raise exc.ImporterError("No role readme found")

        return readme

    def _lint_role(self):
        """Log ansible-lint output.

        ansible-lint stdout are linter violations, they are logged as warnings.
        ansible-lint stderr includes info about vars, file discovery,
        summary of linter violations, config suggestions, and raised errors.
        Only raised errors are logged, they are logged as errors.
        """

        self.log.info(f"Linting role {self.name} via ansible-lint...")

        if not shutil.which("ansible-lint"):
            self.log.warning("ansible-lint not found, skipping lint of role")
            return

        cmd = [
            "/usr/bin/env",
            f"ANSIBLE_LOCAL_TEMP={self.cfg.ansible_local_tmp}",
            "ansible-lint",
            "--profile",
            "production",
            "--parseable",
            "--nocolor",
            self.dirname,
        ]
        if self.cfg.offline_ansible_lint:
            cmd.append("--offline")

        self.log.debug("CMD:", "".join(cmd))

        proc = Popen(cmd, encoding="utf-8", stdout=PIPE, stderr=PIPE)

        try:
            outs, errs = proc.communicate(timeout=120)
        except TimeoutExpired:
            self.log.error("Timeout on call to ansible-lint")
            proc.kill()
            outs, errs = proc.communicate()

        for line in outs.splitlines():
            self.log.warning(line.strip())

        for line in errs.splitlines():
            if line.startswith(constants.ANSIBLE_LINT_ERROR_PREFIXES):
                self.log.error(line.strip())

        self.log.info("...ansible-lint run complete")
