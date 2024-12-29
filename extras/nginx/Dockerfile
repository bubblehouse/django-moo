FROM nginx:1.27.3
LABEL Maintainer="Phil Christensen <phil@bubblehouse.org>"

# Install base dependencies
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       ssl-cert \
    && rm -rf /var/lib/apt/lists/*
