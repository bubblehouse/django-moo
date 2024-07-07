# DjangoMOO
> LambdaMOO on Django

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

Now you should be able to connect to https://localhost/admin and login with the superuser you just created, or login via SSH, described below.

## Login via SSH

In this example, my superuser is called `phil`, and I'm automatically prompted for my password.

    $ ssh localhost -p 8022 -l phil
    (phil@localhost) Password:
    ==> look
    A cavernous laboratory filled with gadgetry of every kind, this seems like a dumping ground for every piece of dusty forgotten equipment a mad scientist might require.
    ==>

It's also possible to associate an SSH Key with your user in the Django Admin so as to skip the password prompt.

When you're done exploring, you can hit `Ctrl-D` to exit.
