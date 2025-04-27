FROM python:3.11.12-slim-bullseye AS builder
LABEL Maintainer="Phil Christensen <phil@bubblehouse.org>"
LABEL Name="django-moo"
LABEL Version="0.37.1"

# Install builder dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       apt-transport-https curl unzip gnupg2 gcc g++ libc-dev libssl-dev libpq-dev \
       python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

ADD poetry.lock .
ADD pyproject.toml .

# Install Python application dependencies
RUN pip install --no-cache-dir -q -U poetry poetry-plugin-export pip \
    && poetry export --with=dev -o requirements.txt \
    && pip install --no-cache-dir -q -r requirements.txt

FROM python:3.11.12-slim-bullseye

# Install base dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       git ssl-cert ssh net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

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

RUN echo "[shell]:8022 $(cat /etc/ssh/ssh_host_ecdsa_key.pub | cut -d ' ' -f 1,2)" > /etc/ssh/pregenerated_known_hosts

ADD . /usr/src/app
ADD extras/entrypoint.sh /entrypoint.sh
ADD extras/uwsgi/uwsgi.ini /etc/uwsgi.ini

# Custom entrypoint for improved ad-hoc command support
ENTRYPOINT ["/entrypoint.sh"]
