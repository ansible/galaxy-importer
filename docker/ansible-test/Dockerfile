FROM quay.io/ansible/default-test-container:3.2.2

RUN useradd user1 \
        --uid 1000 \
        --no-create-home \
        --gid root \
    && mkdir -m 0775 /archive \
    && mkdir -p -m 0775 /ansible_collections \
    && chown user1:root /ansible_collections \
    && pip install ansible-core==2.11.5  # when updating see below
# ansible-core version uses specific default-test-container version, the FROM stmt should be updated
# after quay image is built, tag should be updated in ansible_test/job_template.yaml

# Update dir and permissions for where ansible-test sanity writes files
# NOTE: when container non-privledged, if sanity test writes to new dir, it will fail
RUN touch /usr/local/lib/python3.8/dist-packages/ansible.egg-info \
    && chmod 0775 /usr/local/lib/python3.8/dist-packages/ansible.egg-info \
    && mkdir -m 0775 /.ansible \
    && mkdir -m 0775 /.pylint.d

COPY entrypoint.sh /entrypoint

RUN apt-get update -y \
    && apt-get install -y wget \
    && chmod +x /entrypoint

ENV HOME /
USER 1000

ENTRYPOINT ["/entrypoint"]
