FROM quay.io/ansible/base-test-container:5.10.0

LABEL   com.redhat.component="ansible-test" \
        description="Container used by galaxy for running ansible-test validation." \
        distribution-scope="public" \
        io.k8s.description="Container used by galaxy for running ansible-test validation." \
        maintainer="Red Hat, Inc." \
        name="galaxy-importer" \
        release="0.4.26" \
        summary="Container used by galaxy for running ansible-test validation." \
        url="https://github.com/ansible/galaxy-importer" \
        vendor="Red Hat, Inc." \
        version="0.4.26"

COPY entrypoint.sh /entrypoint

RUN useradd user1 \
      --uid 1000 \
      --no-create-home \
      --gid root && \
    apt-get update -y && \
    apt-get remove -y git && \
    # upgrade all packages except python, as they can conflict with python setup in base image
    apt-mark hold python* && \
    apt-get upgrade -y && \
    apt-get install -y wget && \
    apt-get clean && \
    chmod +x /entrypoint && \
    mkdir -m 0775 /archive && \
    mkdir -p -m 0775 /ansible_collections /ansible_collections/ns /ansible_collections/ns/col && \
    touch /ansible_collections/ns/col/placeholder.txt && \
    # On updating ansible-core version, update the FROM statement to the matching base-test-container version
    python3.11 -m pip install ansible-core==2.16.0 --disable-pip-version-check && \
    python3.11 -m pip install tox && \
    python3.11 -m pip install --upgrade setuptools && \
    # Creates dir with correct permissions for where ansible-test sanity writes files, needed for non-privileged containers
    mkdir -m 0775 -p /.cache/pylint && \
    mkdir -m 0775 -p /eda /eda/tox

COPY eda/tox.ini /eda/tox

ENV HOME /

RUN cd /ansible_collections/ns/col && \
    ansible-test sanity --prime-venvs && \
    chmod -R 0775 /.ansible && \
    export PIP_NO_WHEEL="true" && for VENV in $(find /.ansible/test/venv/sanity.* -name activate); do echo ${VENV}; . ${VENV}; python /.ansible/test/cache/get_pip_*.py; python -m pip install --upgrade setuptools; python -m pip uninstall -y pip; deactivate; done

ENTRYPOINT ["/entrypoint"]

# Ensure local runs and testing run the same as OpenShift, which runs containers with a non-privileged randomized UID
USER 1001
