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

## Overview

### Front-end

The primary front-end interface uses SSH to create a prompt-driven TUI. There's also the typical Django admin GUI provided on the web port, but access to this isn't required for most users.

### Back-end

Apart from a uWSGI-hosted web application, a Django management command is used to launch the SSH server. This uses AsyncSSH to provide a custom shell interface using `prompt-toolkit` and `ptprompt-python`.

### Workers

Celery workers run each verb execution inside a subprocess. This also restricts memory usage and limits the maximum verb runtime (currently 3 seconds), while making it easy to scale the execution capacity of the MOO server.

Celery workers can be launched with the same image as the other components, and under normal development usage will also launch a "Celery Beat" scheduler within the worker.

### Execution Environment

The verb execution tasks all start with a Django `atomic()` block, so any system exceptions will cause a rollback. This also takes care of any data conflicts between verbs.

The primary task execution environment uses Zope's `RestrictedPython` library to create a restricted coding environment where only selected imports are allowed, and access to `_` variables is restricted.
