import logging
from datetime import datetime, timezone
from time import time

from django.contrib.auth import get_user_model

from moo import bootstrap
from moo.core import code, create, lookup
from moo.core.models import Player
from moo.core.models.acl import Access, Permission

log = logging.getLogger(__name__)
User = get_user_model()

repo = bootstrap.initialize_dataset("default")
wizard = lookup("Wizard")

containers = lookup("container class")
containers.name = "Generic Container"
containers.save()

with code.ContextManager(wizard, log.info):
    sys = lookup(1)

    # LambdaMOO special sentinel references (mirrors $nothing, $ambiguous_match, $failed_match)
    sys.set_property("nothing", lookup("nothing"))
    sys.set_property("ambiguous_match", lookup("ambiguous_match"))
    sys.set_property("failed_match", lookup("failed_match"))

    sys.set_property("container", containers)
    containers.set_property("open_key", None)
    containers.set_property("open", False, inherit_owner=True)
    containers.set_property("opaque", False, inherit_owner=True)

    root = create("Root Class", location=None)
    sys.set_property("root_class", root)
    root.add_verb("accept", code="return True")
    root.set_property("description", "")
    root.set_property("key", None)

    rooms = create("Generic Room", parents=[root], location=None)
    sys.set_property("room", rooms)
    rooms.set_property("blessed_object", None)
    rooms.set_property("blessed_task_id", None)
    rooms.set_property("description", "There's not much to see here.")
    rooms.set_property("exits", [])
    rooms.set_property("victim_ejection_message", "You have been ejected from %s by %s.")
    rooms.set_property("ejection_message", "You have ejected %s.")
    rooms.set_property("room_ejection_message", "%s has been ejected by %s.")
    rooms.set_property("residents", [])
    rooms.set_property("free_entry", True)
    rooms.set_property("entrances", [])
    rooms.set_property("dark", False)
    rooms.set_property("content_list_type", 3)

    mail_room = create("Mail Distribution Center", parents=[rooms], location=None)

    player = create("Generic Player", parents=[root], location=None)
    sys.set_property("player", player)
    player.set_property("last_connect_time", time())
    player.set_property("last_connected_time", None)
    player.set_property("ownership_quota", 1000)
    player.set_property("ps", "they", inherit_owner=True)
    player.set_property("po", "them", inherit_owner=True)
    player.set_property("pp", "their", inherit_owner=True)
    player.set_property("pr", "themselves", inherit_owner=True)
    player.set_property("pq", "theirs", inherit_owner=True)
    player.set_property("psc", "They", inherit_owner=True)
    player.set_property("poc", "Them", inherit_owner=True)
    player.set_property("ppc", "Their", inherit_owner=True)
    player.set_property("prc", "Themselves", inherit_owner=True)
    player.set_property("pqc", "Theirs", inherit_owner=True)
    player.set_property("home", None)
    player.set_property("gaglist", [])
    player.set_property("paranoid", False)
    player.set_property("responsible", [])
    player.set_property("lines", 10)
    player.set_property("object_gaglist", [])
    player.set_property("page_absent_msg", "%n is not currently logged in.")
    player.set_property("page_origin_msg", "You sense that %n is looking for you in %x(location).")
    player.set_property("page_echo_msg", "Your message has been sent.")
    player.set_property("whereis_location_msg", "%N is in %x(location).")
    player.set_property("who_location_msg", "%x(location)")
    player.set_property("victim_ejection_msg", "You have been ejected from %s by %s.")

    programmers = create("Generic Programmer", parents=[player], location=None)
    sys.set_property("programmer", programmers)
    wizards = create("Generic Wizard", parents=[programmers], location=None)
    sys.set_property("wizard", wizards)
    wizard.parents.add(wizards)

    thing = create("Generic Thing", parents=[root], location=None)
    sys.set_property("thing", thing)
    thing.set_property("otake_succeeded_msg", "%N picks up %t.")
    thing.set_property("otake_failed_msg", "")
    thing.set_property("take_succeeded_msg", "You take %t.")
    thing.set_property("take_failed_msg", "You can't pick that up.")
    thing.set_property("odrop_succeeded_msg", "%N drops %t.")
    thing.set_property("odrop_failed_msg", "%N tries to drop %t but fails!")
    thing.set_property("drop_succeeded_msg", "You drop %t.")
    thing.set_property("drop_failed_msg", "You can't seem to drop %t here.")
    containers.parents.add(thing)

    furniture = create("Generic Furniture", parents=[thing], location=None)
    sys.set_property("furniture", furniture)
    furniture.set_property("take_failed_msg", "It's not possible to move something like this.")
    furniture.set_property("otake_failed_msg", "%N tries to pick up %t, but it won't budge.")
    furniture.set_property("sit_succeeded_msg", "You sit on %t.")
    furniture.set_property("osit_succeeded_msg", "%N sits on %t.")
    furniture.set_property("sit_failed_msg", "You are already sitting on %t.")
    furniture.set_property("stand_succeeded_msg", "You stand up from %t.")
    furniture.set_property("ostand_succeeded_msg", "%N stands up from %t.")
    furniture.set_property("stand_failed_msg", "You aren't sitting on %t.")

    exits = create("Generic Exit", parents=[root], location=None)
    sys.set_property("exit", exits)
    exits.set_property("source", None)
    exits.set_property("dest", None)
    exits.set_property("nogo_msg", "You can't go that way.")
    exits.set_property("onogo_msg", "{actor} can't go that way.")
    exits.set_property("arrive_msg", "You arrive at {subject}.")
    exits.set_property("oarrive_msg", "{actor} arrives at {subject}.")
    exits.set_property("oleave_msg", "{actor} leaves {subject}.")
    exits.set_property("leave_msg", "You leave {subject}.")

    notes = create("Generic Note", parents=[thing], location=None)
    sys.set_property("note", notes)
    notes.set_property("text", "")
    notes.set_property("read_key", None)

    letters = create("Generic Letter", parents=[notes], location=None)
    sys.set_property("letter", letters)

    lock_utils = create("Lock Utilities", location=None)
    sys.set_property("lock_utils", lock_utils)

    string_utils = create("String Utilities", location=None)
    sys.set_property("string_utils", string_utils)

    match_utils = create("Match Utilities", location=None)
    sys.set_property("match_utils", match_utils)

    gender_utils = create("Gender Utilities", location=None)
    sys.set_property("gender_utils", gender_utils)
    gender_utils.set_property("pronouns", ["ps", "po", "pp", "pr", "pq", "psc", "poc", "ppc", "prc", "pqc"])
    gender_utils.set_property("genders", ["neuter", "male", "female", "plural"])
    gender_utils.set_property("ps", ["it", "he", "she", "they"])
    gender_utils.set_property("po", ["it", "him", "her", "them"])
    gender_utils.set_property("pp", ["its", "his", "her", "their"])
    gender_utils.set_property("pr", ["itself", "himself", "herself", "themselves"])
    gender_utils.set_property("pq", ["its", "his", "hers", "theirs"])
    gender_utils.set_property("psc", ["It", "He", "She", "They"])
    gender_utils.set_property("poc", ["It", "Him", "Her", "Them"])
    gender_utils.set_property("ppc", ["Its", "His", "Hers", "Their"])
    gender_utils.set_property("prc", ["Itself", "Himself", "Herself", "Themselves"])
    gender_utils.set_property("pqc", ["Its", "His", "Hers", "Theirs"])

    lab = create("The Laboratory", parents=[rooms], location=None)
    lab.set_property(
        "description",
        """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""",
    )
    sys.set_property("player_start", lab)

    wizard.location = lab
    wizard.save()

    new_player = create(name="Player", unique_name=True, location=lab)
    p = Player.objects.create()
    p.avatar = new_player
    p.save()

    new_player.parents.add(player)
    new_player.owner = new_player
    new_player.save()

    # The Tradesmen — autonomous builder agents
    # Mason ($player): digs rooms and wires exits
    mason_obj = create(name="Mason", unique_name=True, location=None)
    mason_obj.parents.add(player)
    mason_obj.owner = mason_obj
    mason_obj.save()
    mason_user = User.objects.create_user(username="mason", password="Mxq7vB2nKpL4")
    Player.objects.create(user=mason_user, avatar=mason_obj)

    # Tinker ($programmer): writes verbs for interactive objects and secret exits
    tinker_obj = create(name="Tinker", unique_name=True, location=None)
    tinker_obj.parents.add(programmers)
    tinker_obj.owner = tinker_obj
    tinker_obj.save()
    tinker_user = User.objects.create_user(username="tinker", password="Pw9cX3mZrT6y")
    Player.objects.create(user=tinker_user, avatar=tinker_obj)

    # Joiner ($player): creates furniture and containers
    joiner_obj = create(name="Joiner", unique_name=True, location=None)
    joiner_obj.parents.add(player)
    joiner_obj.owner = joiner_obj
    joiner_obj.save()
    joiner_user = User.objects.create_user(username="joiner", password="Hn4kD8sQvY2f")
    Player.objects.create(user=joiner_user, avatar=joiner_obj)

    # Harbinger ($programmer): creates NPCs, uses @eval for random roll and tell verb
    harbinger_obj = create(name="Harbinger", unique_name=True, location=None)
    harbinger_obj.parents.add(programmers)
    harbinger_obj.owner = harbinger_obj
    harbinger_obj.save()
    harbinger_user = User.objects.create_user(username="harbinger", password="Bt6wF5jRcU3e")
    Player.objects.create(user=harbinger_user, avatar=harbinger_obj)

    # Grant derive to everyone on all standard system classes so any player can
    # create instances via @create without needing wizard privileges.
    derive_perm = Permission.objects.get(name="derive")
    for _cls in [root, thing, rooms, exits, player, programmers, furniture, containers]:
        Access.objects.get_or_create(
            object=_cls, permission=derive_perm,
            type="group", group="everyone", rule="allow",
        )

    root.get_verb("accept").delete()

    containers.get_verb("accept").delete()
    bootstrap.load_verbs(repo, "moo.bootstrap.default_verbs")
    sys.gender_utils.set(player, "plural")
