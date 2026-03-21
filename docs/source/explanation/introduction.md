# Introduction

This document will heavily reference the [LambdaMOO Programmer's Manual](https://www.hayseed.net/MOO/manuals/ProgrammersManual.html), written by Pavel Curtis. The design doc was essential to the development of DjangoMOO, and this updated version will hopefully be as useful to my users as Pavel's doc was to me.

> LambdaMOO is a network-accessible, multi-user, programmable, interactive system well-suited to the construction of text-based adventure games, conferencing systems, and other collaborative software. Its most common use, however, is as a multi-participant, low-bandwidth virtual reality, and it is with this focus in mind that I describe it here.
>
> Participants (usually referred to as players) connect to LambdaMOO using Telnet or some other, more specialized, client program. Upon connection, they are usually presented with a welcome message explaining how to either create a new character or connect to an existing one. Characters are the embodiment of players in the virtual reality that is LambdaMOO.

DjangoMOO has replaced use of the Telnet protocol with SSH.

> Having connected to a character, players then give one-line commands that are parsed and interpreted by LambdaMOO as appropriate. Such commands may cause changes in the virtual reality, such as the location of a character, or may simply report on the current state of that reality, such as the appearance of some object.
>
> The job of interpreting those commands is shared between the two major components in the LambdaMOO system: the server and the database. The server is a program, written in a standard programming language, that manages the network connections, maintains queues of commands and other tasks to be executed, controls all access to the database, and executes other programs written in the MOO programming language. The database contains representations of all the objects in the virtual reality, including the MOO programs that the server executes to give those objects their specific behaviors.

There's a few differences here, mostly because instead of the MOO programming language, DjangoMOO uses plain Python. Access to the database is via the Django ORM, while responsibility for maintaining execution queues is left to Celery. This breaks the implementation up into separate scalable components typical to a modern web application.

> Almost every command is parsed by the server into a call on a MOO procedure, or verb, that actually does the work. Thus, programming in the MOO language is a central part of making non-trivial extensions to the database and thus, the virtual reality.
