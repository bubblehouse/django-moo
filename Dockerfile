FROM python:3.10-slim-bullseye
LABEL Maintainer="Phil Christensen <phil@bubblehouse.org>"
LABEL Name="termiverse"
LABEL Version="0.3.1"

# Install base dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       apt-transport-https curl unzip gnupg2 gcc g++ libc-dev libssl-dev libpq-dev \
       sqlite3 ssl-cert git python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN chgrp www-data /etc/ssl/private/
RUN chmod g+rx /etc/ssl/private/
RUN chgrp www-data /etc/ssl/private/ssl-cert-snakeoil.key
RUN chmod g+r /etc/ssl/private/ssl-cert-snakeoil.key

ADD poetry.lock /usr/src/app/poetry.lock
ADD pyproject.toml /usr/src/app/pyproject.toml

# Install Python application dependencies
WORKDIR /usr/src/app
RUN pip install --no-cache-dir -q -U poetry
RUN poetry export -o requirements.txt
RUN pip install -r requirements.txt

ADD . /usr/src/app
RUN chgrp www-data /usr/src/app
ADD extras/entrypoint.sh /entrypoint.sh
ADD extras/uwsgi/uwsgi.ini /etc/uwsgi.ini

RUN mkdir -p /usr/src/app/static
RUN chgrp www-data /usr/src/app/static/
RUN chmod ug+rwx /usr/src/app/static/

# Custom entrypoint for improved ad-hoc command support
ENTRYPOINT ["/entrypoint.sh"]
