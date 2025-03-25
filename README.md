# DjangoMOO
> "LambdaMOO on Django"

![release](https://gitlab.com/bubblehouse/django-moo/-/badges/release.svg)
![pipeline](https://gitlab.com/bubblehouse/django-moo/badges/main/pipeline.svg?ignore_skipped=true&job=test)
![coverage](https://gitlab.com/bubblehouse/django-moo/badges/main/coverage.svg?job=test)
![quality](https://bubblehouse.gitlab.io/django-moo/badges/lint.svg)
![docs](https://readthedocs.org/projects/django-moo/badge/?version=latest)

DjangoMOO is a game server for hosting text-based online MOO-like games.

## Quick Start
Checkout the project and use Docker Compose to run the necessary components:

    git clone https://gitlab.com/bubblehouse/django-moo
    cd django-moo
    docker compose up

Run `migrate`, `collectstatic`, and bootstrap the initial database with some sample objects and users:

    docker compose run webapp manage.py migrate
    docker compose run webapp manage.py collectstatic
    docker compose run webapp manage.py moo_init
    docker compose run webapp manage.py createsuperuser --username phil
    docker compose run webapp manage.py moo_enableuser --wizard phil Wizard

Now you should be able to connect to https://localhost/ and login with the superuser you just created, described below.

## Login via Web

To make things easier for folks without SSH access or who are behind firewalls, the server interface is exposed through [webssh](https://github.com/huashengdun/webssh).

![WebSSH Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/webssh-client-example.png)

This client is only able to open connections to the local SSH server.

### Admin Interface

As a secondary way to view the contents of a running server, a Django Admin interface is available at `/admin`. It's really a last resort for most things, but it's still the best way to modify verb code in a running server:

![Django Admin Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/django-admin-example.png)

## Login via SSH

Of course, it's also possible (perhaps even preferred) to connect directly over SSH:

![SSH Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/ssh-client-example.png)

It's also possible to associate an SSH Key with your user in the Django Admin so as to skip the password prompt.

When you're done exploring, you can hit `Ctrl-D` to exit.
