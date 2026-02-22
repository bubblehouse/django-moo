FROM python:3.11.12-slim-bullseye AS builder
LABEL Maintainer="Phil Christensen <phil@bubblehouse.org>"
LABEL Name="django-moo"
LABEL Version="0.47.3"

# Install builder dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       apt-transport-https curl unzip gnupg2 gcc g++ libc-dev libssl-dev libpq-dev \
       python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the build tool.
ARG TARGETARCH
RUN case "${TARGETARCH}" in \
      amd64) UV_ARCH="x86_64" ;; \
      arm64) UV_ARCH="aarch64" ;; \
      *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac \
    && curl -L "https://github.com/astral-sh/uv/releases/download/0.10.4/uv-${UV_ARCH}-unknown-linux-gnu.tar.gz" -o uv.tar.gz \
    && tar -xzf uv.tar.gz \
    && mv "uv-${UV_ARCH}-unknown-linux-gnu/uv" /usr/local/bin/uv \
    && chmod 0755 /usr/local/bin/uv \
    && rm -rf uv.tar.gz

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.11 \
    UV_PROJECT_ENVIRONMENT=/usr/app

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync \
        --frozen \
        --no-install-project

COPY . /usr/app/src
WORKDIR /usr/app/src
RUN --mount=type=cache,target=/root/.cache \
    uv sync \
        --frozen \
        --no-dev \
        --no-editable

RUN export SITE_PACKAGES=`../bin/python -c 'import sys; print(sys.path[-1])'` \
    && cp /usr/app/src/extras/webssh/index.html $SITE_PACKAGES/webssh/templates/index.html

FROM python:3.11.12-slim-bullseye

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       git ssl-cert ssh net-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN echo "[shell]:8022 $(cat /etc/ssh/ssh_host_ecdsa_key.pub | cut -d ' ' -f 1,2)" > /etc/ssh/pregenerated_known_hosts

# Setup directories and permissions
RUN chgrp www-data /etc/ssl/private/ \
    && chmod g+rx /etc/ssl/private/ \
    && chgrp www-data /etc/ssl/private/ssl-cert-snakeoil.key \
    && chmod g+r /etc/ssl/private/ssl-cert-snakeoil.key \
    && mkdir -p /usr/src/app \
    && chgrp www-data /usr/src/app \
    && mkdir -p /usr/src/app/static \
    && chgrp www-data /usr/src/app/static/ \
    && chmod ug+rwx /usr/src/app/static/ \
    && chgrp www-data /etc/ssh/ssh_host_ecdsa_key \
    && chmod ug+rw /etc/ssh/ssh_host_ecdsa_key \
    && chgrp www-data /etc/ssh/ssh_host_ecdsa_key.pub \
    && chmod ug+rw /etc/ssh/ssh_host_ecdsa_key.pub


ADD extras/entrypoint.sh /entrypoint.sh
ADD extras/uwsgi/uwsgi.ini /etc/uwsgi.ini

COPY --from=builder /usr/app /usr/app

# Custom entrypoint for improved ad-hoc command support
ENTRYPOINT ["/entrypoint.sh"]
# See <https://hynek.me/articles/docker-signals/>.
STOPSIGNAL SIGINT
