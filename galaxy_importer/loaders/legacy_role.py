import logging
import os
import shutil
from subprocess import PIPE, Popen, TimeoutExpired

from .content import RoleLoader

from galaxy_importer import constants
from galaxy_importer import exceptions as exc
from galaxy_importer import schema

default_logger = logging.getLogger(__name__)


class LegacyRoleLoader(object):
    """Loads legacy role information."""

    def __init__(self, dirname, namespace, cfg=None, logger=None):
        self.log = logger or default_logger
        self.dirname = dirname
        self.namespace = namespace
        self.cfg = cfg

        self.metadata = None
        self.content_obj = None
        self.content = None
        self.name = None
        self.readme_file = None
        self.readme_html = None

    def load(self):
        """Loads role metadata and content information and lints role."""

        self.metadata = self._load_metadata()

        self.content_obj = self._load_content()

        self.name = self.content_obj.name
        self.readme_file = self.content_obj.readme_file
        self.readme_html = self.content_obj.readme_html

        if self.cfg.run_ansible_lint:
            self._lint_role()

        return schema.LegacyImportResult(
            namespace=self.namespace,
            name=self.name,
            metadata=self.metadata,
            readme_file=self.readme_file,
            readme_html=self.readme_html,
        )

    def _load_metadata(self):
        """Loads role metadata."""

        metayaml = None
        for file in constants.ROLE_META_FILES:
            metayaml = os.path.join(self.dirname, file)
            if os.path.exists(metayaml):
                break
        if metayaml is None or not os.path.exists(metayaml):
            raise exc.ImporterError("Metadata not found at any path")
        return schema.LegacyMetadata.parse(metayaml)

    def _load_content(self):
        """Loads role content information."""

        data = RoleLoader(
            constants.ContentType.ROLE,
            self.dirname,
            os.getcwd(),
            None,
            self.cfg,
            self.log,
            True,
        ).load()
        return data

    def _lint_role(self):
        """Log ansible-lint output.

        ansible-lint stdout are linter violations, they are logged as warnings

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
            self.dirname,
            "--parseable",
        ]

        self.log.debug("CMD:", "".join(cmd))

        proc = Popen(
            cmd,
            cwd=os.path.dirname(self.dirname) or os.path.curdir,
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
        )

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
