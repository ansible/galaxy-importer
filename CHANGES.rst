galaxy-importer 0.2.13 (2020-12-16)
===================================

Bugfixes
--------

- Fix the check for max size of docs files (`AAH-220 <https://issues.redhat.com/browse/AAH-220>`_)


galaxy-importer 0.2.12 (2020-12-04)
===================================

Features
--------

- Enables running ansible-test via Podman. (`AAH-5 <https://issues.redhat.com/browse/AAH-5>`_)
- Allow one to customize version for sdist building (`AAH-185 <https://issues.redhat.com/browse/AAH-185>`_)
- Surface ansible-lint exception within galaxy-importer (`AAH-188 <https://issues.redhat.com/browse/AAH-188>`_)


Misc
----

- `AAH-173 <https://issues.redhat.com/browse/AAH-173>`_


galaxy-importer 0.2.11 (2020-11-09)
===================================

No significant changes.


galaxy-importer 0.2.10 (2020-11-09)
===================================

Bugfixes
--------

- Fix local image ansible-test run so won't attempt archive download (`#89 <https://issues.redhat.com/browse/AAH-89>`_)


galaxy-importer 0.2.9 (2020-11-04)
==================================

Features
--------

- Import execution environment metadata when present (`#23 <https://issues.redhat.com/browse/AAH-23>`_)


Misc
----

- `#91 <https://issues.redhat.com/browse/AAH-91>`_


galaxy-importer 0.2.8 (2020-08-28)
==================================

Features
--------

- Enable checking that a collection contains a tag from the required tag list. (`#255 <https://github.com/ansible/galaxy_ng/issues/255>`_)
- In OpenShift replace image build with ansible-test job that downloads archive (`#342 <https://github.com/ansible/galaxy_ng/issues/342>`_)
- Allow galaxy-import to enable/disable ansible-lint based on config (`#353 <https://github.com/ansible/galaxy_ng/issues/353>`_)


Bugfixes
--------

- Add integration test to run galaxy-importer from shell (`#292 <https://github.com/ansible/galaxy_ng/issues/292>`_)
- Standardize importer to require repository in collection metadata (`#293 <https://github.com/ansible/galaxy_ng/issues/293>`_)
- Fix OpenShift template base image reference. (`#338 <https://github.com/ansible/galaxy_ng/issues/338>`_)
- Timeouts for OpenShift image build is increased and made configurable via environment variables: ``IMPORTER_JOB_API_CHECK_RETRIES`` and ``IMPORTER_JOB_API_CHECK_DELAY_SECONDS``. (`#345 <https://github.com/ansible/galaxy_ng/issues/345>`_)
- Fixed OpenShift Job referencing image by name only. Replaced `.metadata.name` with `.image.dockerImageReference`. (`#350 <https://github.com/ansible/galaxy_ng/issues/350>`_)


Misc
----

- `#342 <https://github.com/ansible/galaxy_ng/issues/342>`_, `#355 <https://github.com/ansible/galaxy_ng/issues/355>`_


galaxy-importer 0.2.7 (2020-07-10)
==================================

Bugfixes
--------

- Fix install error when doing pip install from pypi and wheel (`#47 <https://github.com/ansible/galaxy_ng/issues/47>`_)


galaxy-importer 0.2.6 (2020-07-10)
==================================

Features
--------

- Add functionality to run ansible-test via a Docker local image (`#47 <https://github.com/ansible/galaxy_ng/issues/47>`_)
- Update tar subprocess archive extraction (`#222 <https://github.com/ansible/galaxy_ng/issues/222>`_)


Misc
----

- `#75 <https://github.com/ansible/galaxy-importer/pull/75>`_, `#241 <https://github.com/ansible/galaxy_ng/issues/241>`_, `#276 <https://github.com/ansible/galaxy_ng/issues/276>`_


galaxy-importer 0.2.5 (2020-06-10)
==================================

Bugfixes
--------

- Parameterize ansible-test openshift job container timeout (`#230 <https://github.com/ansible/galaxy_ng/issues/230>`_)


Misc
----

- `#67 <https://github.com/ansible/galaxy-importer/pull/67>`_


galaxy-importer 0.2.4 (2020-05-20)
==================================

Features
--------

- Override default configuration file paths with an environment variable (`#148 <https://github.com/ansible/galaxy_ng/issues/148>`_)


Bugfixes
--------

- Returns non-zero exit code on failure to enable use in shell scripts. (`#66 <https://github.com/ansible/galaxy-importer/pull/66>`_)


galaxy-importer 0.2.3 (2020-05-13)
==================================

Bugfixes
--------

- Fix traceback and improve output on unexpected docstring format (`#159 <https://github.com/ansible/galaxy_ng/issues/159>`_)


galaxy-importer 0.2.2 (2020-05-12)
==================================

Bugfixes
--------

- Parameterize openshift container sizing to fix scheduling issues (`#122 <https://github.com/ansible/galaxy_ng/issues/122>`_)


galaxy-importer 0.2.1 (2020-05-04)
==================================

Bugfixes
--------

- Fix openshift container import fails on checking sanity container status (`#130 <https://github.com/ansible/galaxy_ng/issues/130>`_)


Misc
----

- `#132 <https://github.com/ansible/galaxy_ng/issues/132>`_


galaxy-importer 0.2.0 (2020-04-02)
==================================

Features
--------

- Support running flake8 on plugins per config, defaulted to false (`#55 <https://github.com/ansible/galaxy-importer/pull/55>`_)
- Update python dependency versions (`#56 <https://github.com/ansible/galaxy-importer/pull/56>`_)
- Add towncrier for changelog management (`#59 <https://github.com/ansible/galaxy-importer/pull/59>`_)


Bugfixes
--------

- Use absoulte path when loading role metadata file (`#54 <https://github.com/ansible/galaxy-importer/pull/54>`_)
- Improve openshift job error handling and increase container size (`#57 <https://github.com/ansible/galaxy-importer/pull/57>`_)


Improved Documentation
----------------------

- Describe process around issues and releases (`#58 <https://github.com/ansible/galaxy-importer/pull/58>`_)
