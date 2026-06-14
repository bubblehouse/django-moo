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
.. autofunction:: moo.sdk.ensure_player_record
   :no-index:
.. autofunction:: moo.sdk.remove_player_record
   :no-index:
```

## Tasks and continuations

```{eval-rst}
.. autofunction:: moo.sdk.invoke
   :no-index:
.. autofunction:: moo.sdk.cancel_scheduled_task
   :no-index:
.. autofunction:: moo.sdk.get_scheduled_task_info
   :no-index:
.. autofunction:: moo.sdk.task_time_low
   :no-index:
.. autofunction:: moo.sdk.schedule_continuation
   :no-index:
.. autofunction:: moo.sdk.set_task_perms
   :no-index:
.. autofunction:: moo.sdk.moo_eval
   :no-index:
.. autofunction:: moo.sdk.invoked_verb_name
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
.. autofunction:: moo.sdk.can_open_editor
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

## Accounts and identity

The {class}`~moo.core.models.auth.Player` row is the durable account behind an
avatar; these resolve between an avatar and its account.

```{eval-rst}
.. py:currentmodule:: moo.sdk
.. autofunction:: moo.sdk.account_for
   :no-index:
.. autofunction:: moo.sdk.avatars_of
   :no-index:
.. autofunction:: moo.sdk.account_id_for
   :no-index:
.. autofunction:: moo.sdk.current_account
   :no-index:
```

## Provenance and tagged output

Every published message carries a server-computed provenance triple, recorded
always; sanctioned output forms carry a structural ``kind`` tag the client
renders so a user line cannot present as a system line or another actor.

```{eval-rst}
.. autofunction:: moo.sdk.notify
   :no-index:
.. autofunction:: moo.sdk.current_provenance
   :no-index:
.. autofunction:: moo.sdk.capture_provenance_stack
   :no-index:
.. autofunction:: moo.sdk.resolve_provenance_account
   :no-index:
```

## Flood limiting

```{eval-rst}
.. autofunction:: moo.sdk.broadcast_allowed
   :no-index:
.. autofunction:: moo.sdk.broadcast_limit
   :no-index:
.. autofunction:: moo.sdk.broadcast_window
   :no-index:
```

## Moderation: suspend and ban

Staff-gated sanctions keyed to the durable account; neither can target staff.

```{eval-rst}
.. autofunction:: moo.sdk.suspend
   :no-index:
.. autofunction:: moo.sdk.unsuspend
   :no-index:
.. autofunction:: moo.sdk.ban
   :no-index:
.. autofunction:: moo.sdk.is_blacklisted
   :no-index:
.. autofunction:: moo.sdk.account_login_blocked
   :no-index:
```

## Onboarding: guests and registration

```{eval-rst}
.. autofunction:: moo.sdk.provision_guest
   :no-index:
.. autofunction:: moo.sdk.remove_guest
   :no-index:
.. autofunction:: moo.sdk.is_guest
   :no-index:
.. autofunction:: moo.sdk.register
   :no-index:
.. autofunction:: moo.sdk.require_registered
   :no-index:
```

## Audit log

```{eval-rst}
.. autofunction:: moo.sdk.record_action
   :no-index:
.. autofunction:: moo.sdk.query_audit
   :no-index:
```

## Non-destructive recovery

``@recycle`` is now a reversible soft-recycle; ``@destroy`` is the permanent
delete. Soft-recycled objects are hidden from the site-scoped manager but keep
their id and inbound references.

```{eval-rst}
.. autofunction:: moo.sdk.soft_recycle
   :no-index:
.. autofunction:: moo.sdk.restore
   :no-index:
.. autofunction:: moo.sdk.destroy
   :no-index:
.. autofunction:: moo.sdk.get_recycled
   :no-index:
.. autofunction:: moo.sdk.sweep_recycled
   :no-index:
```

## Escape guarantee and connectivity

```{eval-rst}
.. autofunction:: moo.sdk.guaranteed_moveto
   :no-index:
.. autofunction:: moo.sdk.send_home
   :no-index:
.. autofunction:: moo.sdk.check_room_connectivity
   :no-index:
```

## Indexed external keys

```{eval-rst}
.. autofunction:: moo.sdk.resolve_by_key
   :no-index:
.. autofunction:: moo.sdk.get_or_create_by_key
   :no-index:
```
