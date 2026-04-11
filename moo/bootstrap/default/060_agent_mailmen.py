# pylint: disable=undefined-variable,wrong-import-position
# The Mailmen — autonomous mail-writing agents
# Cliff ($player): pompous know-it-all postal worker (Cliff Clavin from Cheers)
cliff_obj, _ = bootstrap.get_or_create_object("Cliff", unique_name=True, parents=[player])
cliff_obj.owner = cliff_obj
cliff_obj.set_property("home", lab)
cliff_obj.save()
cliff_user, cliff_created = User.objects.get_or_create(username="cliff")
if cliff_created:
    cliff_user.set_password("CQ7I0aiJ8U7KGV9t")
    cliff_user.save()
cliff_player, _ = Player.objects.get_or_create(user=cliff_user, defaults=dict(avatar=cliff_obj))

# Newman ($player): bitter, conspiratorial postal worker (Newman from Seinfeld)
newman_obj, _ = bootstrap.get_or_create_object("Newman", unique_name=True, parents=[player])
newman_obj.owner = newman_obj
newman_obj.set_property("home", lab)
newman_obj.save()
newman_user, newman_created = User.objects.get_or_create(username="newman")
if newman_created:
    newman_user.set_password("bORbxkxKws5IFhj2")
    newman_user.save()
newman_player, _ = Player.objects.get_or_create(user=newman_user, defaults=dict(avatar=newman_obj))

# Seed mail: Cliff opens with a dismissive two-word note so Newman has something to react to
from moo.sdk.mail import send_message as _send_message

if not cliff_obj.sent_messages.exists():
    _send_message(cliff_obj, [newman_obj], "Hello, Newman.", "Hello, Newman.")
