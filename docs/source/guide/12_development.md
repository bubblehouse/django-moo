# Development

Beyond crafting content in-game, there's a lot more development tooling that can be used to
work on the core functions of django-moo.

## Prerequisites

* Docker
* VSCode
  *  with [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) plugin

## Getting Started

In the django-moo README there are instructions on setting up Docker and using Docker Compose
to run the application stack. You'll still want to follow them all:

> Checkout the project and use Docker Compose to run the necessary components:
>
>     git clone https://gitlab.com/bubblehouse/django-moo
>     cd django-moo
>     docker compose up
>
> Run `migrate`, `collectstatic`, and bootstrap the initial database with some sample objects and users:
>
>     docker compose run webapp manage.py migrate
>     docker compose run webapp manage.py collectstatic
>     docker compose run webapp manage.py moo_init
>     docker compose run webapp manage.py createsuperuser --username phil
>     docker compose run webapp manage.py moo_enableuser --wizard phil Wizard

Once this part is complete, though, you'll want to open up the project folder in VSCode. You should be prompted to
reopen the project as a Dev Container, if not, invoke "Dev Containers: Reopen in Container" from the command bar.

## Using VSCode with django-moo

The first thing to do with your development environment is to make sure you can run the unit tests:

![django-moo unit tests](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/vscode-testing.png)

In addition to testing core functionality, there's also integration tests for the default verbs at creation time.

### Running the Server

The Dev Containers use the Compose file normally, except for the Celery broker, which isn't run by default. Instead
the terminals you create will all be on the `celery` container instance, and you can run the Celery server in debug
mode using the launch job on the "Run and Debug" tab.

![django-moo debugging](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/vscode-debug.png)
