# Architecture

## Goals

While DjangoMOO's overarching goals are fairly similar to that of LambdaMOO's,
the details of how it's been implemented are substantially different:

* 100% Python – both the implementation and the internal game language are Python, which drives many other design details
* Django-backed – uses as many native Django features to reduce complexity and make the codebase easier to work on.
* Celery-backed – uses a standard backend task queue with numerous deployment options

Although this does require a number of "moving pieces", they're easily launched by the included Docker Compose file, and should be similarly easy to deploy in a full-time production scenario. The end result is a deployment that is:

* Highly available – able to withstand failure of duplicate components
* Highly scalable – all the components of the stack are easily scaled, either horizontally or vertically
* Easy to develop on – common conventions are used as much as possible

A final goal is for the software to be cheap to deploy, but that has several variables not worth getting into here.

### antioch, a predecessor to django-moo

A lot of the architecture decisions and proofs of concepts for `django-moo` come from lessons learned building [antioch](https://github.com/philchristensen/antioch).

The original goals for antioch were to add on to the MOO concept in a way that allowed for a fully graphical UI. These goals also predated Django and other helpful frameworks; as antioch's inception was in 1999-2000, many of these tools didn't exist or were in their infancy. Although over time antioch began to modernize, there was a lot of custom code that would be better replaced by standard libraries.

This led to a series of "revelations" that guide `django-moo` development today:

* As a niche project, any third-party library that can reduce development overhead is worth it.
* As a gaming-adjacent project, it's impossible to complete with modern graphical games, so don't prioritize that.
* The graphical limitations of the Telnet era of MOO were actually a storytelling benefit.
* For something of this size, ease of testing needs to be planned for from the beginning.

## Overview

### Front-end

The primary front-end interface uses SSH to create a prompt-driven TUI. The web port serves three things: the Django admin for wizard-level management, a browser-based SSH terminal (WebSSH), and a registration flow for new players.

#### Player Registration

New players register through a web form powered by [django-allauth](https://allauth.org/). The registration form collects the standard allauth credentials (username, email, password) plus MOO-specific fields: character name, gender, and an optional description. On successful submission, a MOO `Object` avatar is created and linked to the Django user account via a `Player` record.

The form is defined in `moo/shell/forms.py` (`SignupForm`). The view in `moo/shell/views.py` (`SignupView`) overrides allauth's default behaviour so that an already-authenticated user who clicks "Sign Up" is silently logged out before the new registration proceeds, rather than being redirected away.

Template overrides live in `moo/shell/templates/`. A shared `base.html` provides the Bootstrap styles used by the terminal page and all allauth pages. `allauth/layouts/base.html` is overridden so every page in the authentication flow (login, logout, email verification, password reset) inherits the same look without per-page template copies.

### Back-end

Apart from a uWSGI-hosted web application, a Django management command is used to launch the SSH server. This uses AsyncSSH to provide a custom shell interface using `prompt-toolkit` and `ptprompt-python`.

### Workers

Celery workers run each verb execution inside a subprocess. This also restricts memory usage and limits the maximum verb runtime (currently 3 seconds), while making it easy to scale the execution capacity of the MOO server.

Celery workers can be launched with the same image as the other components, and under normal development usage will also launch a "Celery Beat" scheduler within the worker.

### Execution Environment

The verb execution tasks all start with a Django `atomic()` block, so any system exceptions will cause a rollback. This also takes care of any data conflicts between verbs.

The primary task execution environment uses Zope's `RestrictedPython` library to create a restricted coding environment where only selected imports are allowed, and access to `_` variables is restricted.
