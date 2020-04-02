## Process

Notes about the process surrounding the `galaxy-importer` package, which is a dependency of projects such as:
* Automation Hub [galaxy_ng](https://github.com/ansible/galaxy_ng)
* [pulp-ansible](https://github.com/pulp/pulp-ansible)
* Community Galaxy [galaxy](https://github.com/ansible/galaxy)

#### Issues and pull requests

* Issues for enhancements or fixes are located on [galaxy_ng](https://github.com/ansible/galaxy_ng)
* Pull Requests in `galaxy-importer` should include a changelog file inside `CHANGES/` and a label for release: `release/x.x.x`
* Changelog filename should be the number of the PR, and the extension of `.feature`, `.bugfix`, `.doc`, `.removal`, or `.misc` - see [towncrier](https://github.com/hawkowl/towncrier#news-fragments) for descriptions of each extension. Example: `CHANGES/56.feature`. File contents should be a one line description of the change.

#### Release steps

* Test `master` branch against `pulp-ansible` functional tests inside `galaxy_ng` development environment
* Run `$ towncrier` to update `CHANGELOG.rst`
* Commit updated version `galaxy_importer/__init__.py` and updated `CHANGELOG.rst`
* Tag the commit with same version number
* Publish to PyPi

#### Testing in other systems

* Latest `galaxy-importer` release will get consumed into `pulp-ansible` nightly builds
* Automation Hub [galaxy_ng](https://github.com/ansible/galaxy_ng) issues labeled `area/importer` will include a `galaxy_ng` PR with associated release of `galaxy-importer`, and get tagged for QE
* Community Galaxy [galaxy](https://github.com/ansible/galaxy) importer issues will include a `galaxy` PR with new release of `galaxy-importer`, and get tagged for QE
