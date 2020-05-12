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
