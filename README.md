# termiverse
> LambdaMOO on Django



![release](https://gitlab.com/bubblehouse/termiverse/-/badges/release.svg)
![pipeline](https://gitlab.com/bubblehouse/termiverse/badges/main/pipeline.svg?ignore_skipped=true&job=test)
![coverage](https://gitlab.com/bubblehouse/termiverse/badges/main/coverage.svg?job=test)


Termiverse is a game server for hosting text-based online MOO-like games.

## Quick Start
Checkout the project and use Docker Compose to run the necessary components:

    git clone https://gitlab.com/bubblehouse/termiverse
    cd termiverse
    docker compose up

Run `migrate`, `collectstatic`, and bootstrap the initial database with some sample objects and users:

    docker compose run webapp manage.py migrate
    docker compose run webapp manage.py collectstatic
    docker compose run webapp manage.py termiverse_init
    docker compose run webapp manage.py createsuperuser

Now you should be able to connect to https://localhost/admin and login with the superuser you just created.

Naviagte through the Django Admin interface to your user record, and associate it with an avatar (usually `#2 (Wizard)`) and check the box to make it a "wizard", i.e., a superuser inside the new universe.

## Login via SSH

In this example, my super user is called `phil`, and I'm automatically prompted for my password.

    $ ssh localhost -p 8022 -l phil
    (phil@localhost) Password:
    ==> look
    A cavernous laboratory filled with gadgetry of every kind, this seems like a dumping ground for every piece of dusty forgotten equipment a mad scientist might require.
    ==>

It's also possible to associate an SSH Key with your user in the Django Admin so as to skip the password prompt.

When you're done exploring, you can hit `Ctrl-D` to exit.
