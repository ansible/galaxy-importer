FROM quay.io/ansible/base-test-container:3.9.0

COPY entrypoint.sh /entrypoint

RUN useradd user1 \
      --uid 1000 \
      --no-create-home \
      --gid root && \
    apt-get update -y && \
    # upgrade all packages except python, as they can conflict with python setup in base image
    apt-mark hold python* && \
    apt-get upgrade -y && \
    apt-get install -y wget && \
    chmod +x /entrypoint && \
    mkdir -m 0775 /archive && \
    mkdir -p -m 0775 /ansible_collections /ansible_collections/ns /ansible_collections/ns/col && \
    touch /ansible_collections/ns/col/placeholder.txt && \
    # On updating ansible-core version, update the FROM statement to the matching base-test-container version
    python3.9 -m pip install ansible-core==2.14.1 --disable-pip-version-check && \
    # Creates dir with correct permissions for where ansible-test sanity writes files, needed for non-privileged containers
    mkdir -m 0775 -p /.cache/pylint

ENV HOME /

RUN cd /ansible_collections/ns/col && \
    ansible-test sanity --prime-venvs && \
    chmod -R 0775 /.ansible

ENTRYPOINT ["/entrypoint"]

# Ensure local runs and testing run the same as OpenShift, which runs containers with a non-privileged randomized UID
USER 1001
