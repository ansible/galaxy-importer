galaxy-importer 0.4.18 (2023-12-06)
===================================

No significant changes.


galaxy-importer 0.4.17 (2023-12-05)
===================================

Bugfixes
--------

- Raise exceptions with invalid paths in collection tarballs. (`AAH-2992 <https://issues.redhat.com/browse/AAH-2992>`_)


galaxy-importer 0.4.16 (2023-11-03)
===================================

Bugfixes
--------

- Allow dictionary type for role dependencies. (`AAH-2823 <https://issues.redhat.com/browse/AAH-2823>`_)


galaxy-importer 0.4.15 (2023-10-31)
===================================

Bugfixes
--------

- Allow underscores for old galaxy role namespace names. (`AAH-2820 <https://issues.redhat.com/browse/AAH-2820>`_)


galaxy-importer 0.4.14 (2023-10-11)
===================================

Misc
----

- Add namespace parameter to legacy role schema checks
- Adding Collection Path Variable to Ansible-Lint Call
- Increase ansible-lint timeout to 180s


galaxy-importer 0.4.13 (2023-08-22)
===================================

Features
--------

- Add offline_ansible_lint configuration, defaulted to True (`AAH-2606 <https://issues.redhat.com/browse/AAH-2606>`_)


galaxy-importer 0.4.12 (2023-08-08)
===================================

Misc
----

- `AAH-1881 <https://issues.redhat.com/browse/AAH-1881>`_, `AAH-2584 <https://issues.redhat.com/browse/AAH-2584>`_


galaxy-importer 0.4.11 (2023-06-23)
===================================

Features
--------

- Adding `ansible-lint` collection level call for the `ansible-lint` Production profile and removing the `ansible-lint` role level call. (`AAH-2202 <https://issues.redhat.com/browse/AAH-2202>`_)
- Adding EDA testing with `tox`, containing the `ruff`, `darglint`, and `pylint` linters. (`AAH-2307 <https://issues.redhat.com/browse/AAH-2307>`_)
- Support importing legacy roles and yielding data, including linting (`AAH-2356 <https://issues.redhat.com/browse/AAH-2356>`_)


Misc
----

- `AAH-2350 <https://issues.redhat.com/browse/AAH-2350>`_


galaxy-importer 0.4.10 (2023-04-25)
==================================

Features
--------

- Find and load eda extensions into content list (`AAH-2311 <https://issues.redhat.com/browse/AAH-2311>`_)


galaxy-importer 0.4.9 (2023-04-18)
==================================

Bugfixes
--------

- Prevent deadlock in os process call (`AAH-2145 <https://issues.redhat.com/browse/AAH-2145>`_)

Misc
----
- Update ansible-builder dependency range


galaxy-importer 0.4.8 (2023-04-06)
==================================

Bugfixes
--------

- Forward compatibilty with ansible-builder


galaxy-importer 0.4.7 (2023-04-03)
==================================

Features
--------

- Modifying the certification changelog check to also check for changelogs under `CHANGELOG.md` and `changelogs/changelog.yaml`. (`AAH-2086 <https://issues.redhat.com/browse/AAH-2086>`_)


Misc
----

- `AAH-1880 <https://issues.redhat.com/browse/AAH-1880>`_, `AAH-2040 <https://issues.redhat.com/browse/AAH-2040>`_, `AAH-2049 <https://issues.redhat.com/browse/AAH-2049>`_, `AAH-2214 <https://issues.redhat.com/browse/AAH-2214>`_


galaxy-importer 0.4.6 (2022-11-01)
==================================

Misc
----

- `AAH-1742 <https://issues.redhat.com/browse/AAH-1742>`_, `AAH-1951 <https://issues.redhat.com/browse/AAH-1951>`_


galaxy-importer 0.4.5 (2022-05-17)
==================================

Features
--------

- Changed ``import_collection`` to work off of a fileobject without requiring an filesystem entry. (`AAH-1506 <https://issues.redhat.com/browse/AAH-1506>`_)


Bugfixes
--------

- Change 'requires_ansible' to use custom ansible ver spec instead of semver (`AAH-981 <https://issues.redhat.com/browse/AAH-981>`_)


galaxy-importer 0.4.4 (2022-05-09)
==================================

Features
--------

- Output an error if no changelog.rst file is present in the root of the collection (`AAH-1460 <https://issues.redhat.com/browse/AAH-1460>`_)


galaxy-importer 0.4.3 (2022-03-24)
==================================

Bugfixes
--------

- Update base container for ansible-test image to support ansible-core 2.12 (`AAH-1127 <https://issues.redhat.com/browse/AAH-1127>`_)


Misc
----

- `AAH-1106 <https://issues.redhat.com/browse/AAH-1106>`_, `AAH-1429 <https://issues.redhat.com/browse/AAH-1429>`_


galaxy-importer 0.4.2 (2021-11-11)
==================================

Features
--------

- Update ansible-test container definition to ansible-core 2.12 (`AAH-946 <https://issues.redhat.com/browse/AAH-946>`_)


galaxy-importer 0.4.1 (2021-11-02)
==================================

Features
--------

- Update ansible-test image definition, including use of py3.8 (`AAH-814 <https://issues.redhat.com/browse/AAH-814>`_)
- Provide binary artifact and add sync_collection() interface (`AAH-979 <https://issues.redhat.com/browse/AAH-979>`_)


galaxy-importer 0.4.0 (2021-08-25)
==================================

Features
--------

- Check for execution environment dependency files (`AAH-539 <https://issues.redhat.com/browse/AAH-539>`_)
- Log when tests/sanity/ignore*.txt exists during import (`AAH-540 <https://issues.redhat.com/browse/AAH-540>`_)
- Add config option to require collection version be at least '1.0.0', defaulted to off (`AAH-667 <https://issues.redhat.com/browse/AAH-667>`_)


Deprecations and Removals
-------------------------

- Remove unused entrypoints and refactor loaders (`AAH-866 <https://issues.redhat.com/browse/AAH-866>`_)


Misc
----

- `AAH-688 <https://issues.redhat.com/browse/AAH-688>`_


galaxy-importer 0.3.4 (2021-06-24)
==================================

No significant changes.


galaxy-importer 0.3.3 (2021-06-14)
==================================

Features
--------

- Validate FILES.json and the chksums of files it defines. (`AAH-403 <https://issues.redhat.com/browse/AAH-403>`_)
- Make `requires_ansible` in meta/runtime.yml mandatory (`AAH-538 <https://issues.redhat.com/browse/AAH-538>`_)
- Update openshift job runner for ansible-test to use image with ansible-core 2.11 (`AAH-559 <https://issues.redhat.com/browse/AAH-559>`_)


galaxy-importer 0.3.2 (2021-05-10)
==================================

Features
--------

- Update deps and move from ansible 2.9 to ansible-core 2.11 (`AAH-588 <https://issues.redhat.com/browse/AAH-588>`_)


galaxy-importer 0.3.1 (2021-04-08)
==================================

Features
--------

- Use file_url from caller for remote storage (`AAH-431 <https://issues.redhat.com/browse/AAH-431>`_)


galaxy-importer 0.3.0 (2021-03-10)
==================================

Bugfixes
--------

- Fix ansible-lint exceptions for collection modules in roles (`AAH-51 <https://issues.redhat.com/browse/AAH-51>`_)


Deprecations and Removals
-------------------------

- Remove no longer needed execution environment logic and tests. (`AAH-7 <https://issues.redhat.com/browse/AAH-7>`_)


galaxy-importer 0.2.16 (2021-02-10)
===================================

Features
--------

- Move execution_environment from docs_blob to top-level importer result (`AAH-7 <https://issues.redhat.com/browse/AAH-7>`_)


galaxy-importer 0.2.15 (2021-02-08)
===================================

Bugfixes
--------

- Update 'bleach' to 3.3.0 to fix 'xss mutation' CVE (`AAH-327 <https://issues.redhat.com/browse/AAH-327>`_)
- Update bleach-allowlist, upstream package name has changed. (`AAH-328 <https://issues.redhat.com/browse/AAH-328>`_)


galaxy-importer 0.2.14 (2021-01-28)
===================================

Features
--------

- Check collection metadata fields for maximum length (`AAH-55 <https://issues.redhat.com/browse/AAH-55>`_)
- Validate and return requires_ansible in importer result (`AAH-231 <https://issues.redhat.com/browse/AAH-231>`_)


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
