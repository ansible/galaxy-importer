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
