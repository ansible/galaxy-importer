FROM quay.io/ansible/default-test-container:1.12

RUN useradd user1 \
        --uid 1000 \
        --no-create-home \
        --gid root \
    && mkdir -m 0775 /archive \
    && mkdir -p -m 0775 /ansible_collections \
    && chown user1:root /ansible_collections \
    && pip install ansible==2.9.10

# Update dir and permissions for where ansible-test sanity writes files
# NOTE: when container non-privledged, if sanity test writes to new dir, it will fail
RUN touch /usr/local/lib/python3.6/dist-packages/ansible.egg-info \
    && chmod 0775 /usr/local/lib/python3.6/dist-packages/ansible.egg-info \
    && mkdir -m 0775 /.ansible \
    && mkdir -m 0775 /.pylint.d

RUN apt-get update -y \
    && apt-get install -y wget \
    && wget -O entrypoint.sh https://raw.githubusercontent.com/ansible/galaxy-importer/master/docker/ansible-test/entrypoint.sh \
    && cp entrypoint.sh /entrypoint \
    && chmod +x /entrypoint

ENV HOME /
USER 1000

ENTRYPOINT ["/entrypoint"]
