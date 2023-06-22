## Process

Notes about the process surrounding the `galaxy-importer` package, which is a dependency of projects such as:
* Automation Hub [galaxy_ng](https://github.com/ansible/galaxy_ng)
* [pulp-ansible](https://github.com/pulp/pulp-ansible)
* Community Galaxy [galaxy](https://github.com/ansible/galaxy)

#### Issues and pull requests

* Issues are located at [issues.redhat.com JIRA](https://issues.redhat.com/issues/?jql=project=AAH)
* Add a changelog entry to `CHANGES/`. Changelog filename should be the number of the JIRA issue, and the extension of `.feature`, `.bugfix`, `.doc`, `.removal`, or `.misc` - see [towncrier](https://github.com/hawkowl/towncrier#news-fragments) for descriptions of each extension. Example: `CHANGES/56.feature`. File contents should be a one line description of the change.
* At least one commit must include a reference to a Jira issue on a single line in the format of `Issue: AAH-1111`
* If Pull Request is small enough not to need a Jira issue, at least one commit must include a single line with `No-Issue`
* Please run the tests in `Makefile` or install the pre-commit hook in `hooks/pre-commit` and correct any failures prior to submitting a pull request.

#### galaxy-importer Roadmap

* [Prioritized list of tickets](https://issues.redhat.com/issues/?jql=project%20in%20(AAH%2C%20AAP%2C%20ANSTRAT)%20AND%20resolution%20%3D%20Unresolved%20AND%20labels%20%3D%20importer%20ORDER%20BY%20priority%20DESC) labeled `importer`

#### Versioning

Versioning (x.y.z) following https://semver.org/
* Advance the x-stream if breaking backwards-compatibility
* Advance the y-stream for new features
* Advance the z-stream for bugfixes / ci / minor changes

#### Release steps

* Open PR with title `Release #.#.#`
  * Update `galaxy_importer/__init__.py` with new version number
    * Be aware of `galaxy-importer` version range dependencies in [pulp_ansible](https://github.com/pulp/pulp_ansible/blob/main/requirements.txt) and [galaxy_ng](https://github.com/ansible/galaxy_ng/blob/master/setup.py)
  * Run `$ towncrier` to update `CHANGES.rst`
* Merge PR
* Check the master branch CI on the merged commit to ensure it is green
* Tag the commit `v<#.#.#>`, and push the tag to upstream repo
* Check the master branch CI on the merged and tagged commit, it will execute a new job to publish to pypi

#### Testing in other systems

* Latest `galaxy-importer` release will get consumed into `pulp-ansible` nightly builds
* Automation Hub [JIRA AAH issues](https://issues.redhat.com/issues/?jql=project=AAH) may specify a `galaxy-importer` change and a `galaxy_ng` PR will include a new release of `galaxy-importer` for testing by QE
* Community Galaxy [galaxy](https://github.com/ansible/galaxy) importer issues will include a `galaxy` PR with new release of `galaxy-importer`, and get tagged for QE
