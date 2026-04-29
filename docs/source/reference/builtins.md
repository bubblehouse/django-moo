# SDK Functions

Every name listed here is exported from `moo.sdk` and importable in
verb code (`from moo.sdk import lookup, create, ...`). For methods
defined on the `Object` model and accessible as `obj.<name>(...)`,
see {doc}`objects`. For `Property` and `Verb` field reference, see
{doc}`properties` and {doc}`verbs`.

## Object lifecycle and lookup

```{eval-rst}
.. py:currentmodule:: moo.sdk
.. autofunction:: moo.sdk.lookup
   :no-index:
.. autofunction:: moo.sdk.create
   :no-index:
.. autofunction:: moo.sdk.players
   :no-index:
.. autofunction:: moo.sdk.connected_players
   :no-index:
.. autofunction:: moo.sdk.owned_objects
   :no-index:
.. autofunction:: moo.sdk.owned_objects_by_pks
   :no-index:
```

## Tasks and continuations

```{eval-rst}
.. autofunction:: moo.sdk.invoke
   :no-index:
.. autofunction:: moo.sdk.task_time_low
   :no-index:
.. autofunction:: moo.sdk.schedule_continuation
   :no-index:
.. autofunction:: moo.sdk.set_task_perms
   :no-index:
.. autofunction:: moo.sdk.moo_eval
   :no-index:
```

## Output and full-screen UIs

```{eval-rst}
.. autofunction:: moo.sdk.write
   :no-index:
.. autofunction:: moo.sdk.open_editor
   :no-index:
.. autofunction:: moo.sdk.open_paginator
   :no-index:
```

## Session settings and client capabilities

```{eval-rst}
.. autofunction:: moo.sdk.get_client_mode
   :no-index:
.. autofunction:: moo.sdk.get_wrap_column
   :no-index:
.. autofunction:: moo.sdk.get_session_setting
   :no-index:
.. autofunction:: moo.sdk.set_session_setting
   :no-index:
```

## Out-of-band MUD-client protocols

```{eval-rst}
.. autofunction:: moo.sdk.send_gmcp
   :no-index:
.. autofunction:: moo.sdk.play_sound
   :no-index:
.. autofunction:: moo.sdk.room_info_payload
   :no-index:
```

## Server administration

```{eval-rst}
.. autofunction:: moo.sdk.boot_player
   :no-index:
.. autofunction:: moo.sdk.server_info
   :no-index:
```

## Mail Functions

```{eval-rst}
.. py:currentmodule:: moo.sdk
.. autofunction:: moo.sdk.send_message
   :no-index:
.. autofunction:: moo.sdk.get_mailbox
   :no-index:
.. autofunction:: moo.sdk.get_message
   :no-index:
.. autofunction:: moo.sdk.mark_read
   :no-index:
.. autofunction:: moo.sdk.delete_message
   :no-index:
.. autofunction:: moo.sdk.undelete_message
   :no-index:
.. autofunction:: moo.sdk.count_unread
   :no-index:
.. autofunction:: moo.sdk.get_mail_stats
   :no-index:
```
