import logging
from time import time

from moo import bootstrap
from moo.core import code, create, lookup
from moo.core.models import Player, User

log = logging.getLogger(__name__)

repo = bootstrap.initialize_dataset("default")
wizard = lookup("Wizard")
user = User.objects.create(username="wizard")
Player.objects.create(user=user, avatar=wizard, wizard=True)

containers = lookup("container class")
containers.name = "Generic Container"
containers.save()

with code.ContextManager(wizard, log.info):
    sys = lookup(1)

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
    player.set_property("page_origin_msg", "You sense that %s is looking for you in %s.")
    player.set_property("page_echo_msg", "Your message has been sent.")
    player.set_property("whereis_location_msg", "%s is in %s.")
    player.set_property("who_location_msg", "%l")

    programmers = create("Generic Programmer", parents=[player], location=None)
    sys.set_property("programmer", programmers)
    wizards = create("Generic Wizard", parents=[programmers], location=None)
    sys.set_property("wizard", wizards)
    wizard.parents.add(wizards)

    thing = create("Generic Thing", parents=[root], location=None)
    sys.set_property("thing", thing)
    thing.set_property("otake_succeeded_msg", "{actor} picks up {subject}.")
    thing.set_property("otake_failed_msg", "")
    thing.set_property("take_succeeded_msg", "You take {subject}.")
    thing.set_property("take_failed_msg", "You can't pick that up.")
    thing.set_property("odrop_succeeded_msg", "{actor} drops {subject}.")
    thing.set_property("odrop_failed_msg", "{actor} tries to drop {subject} but fails!")
    thing.set_property("drop_succeeded_msg", "You drop {subject}.")
    thing.set_property("drop_failed_msg", "You can't seem to drop {subject} here.")
    containers.parents.add(thing)

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
    letters = create("Generic Letter", parents=[notes], location=None)
    sys.set_property("letter", letters)

    lock_utils = create("Lock Utilities", location=None)
    sys.set_property("lock_utils", lock_utils)

    string_utils = create("String Utilities", location=None)
    sys.set_property("string_utils", string_utils)

    gender_utils = create("Gender Utilities", location=None)
    sys.set_property("gender_utils", gender_utils)
    gender_utils.set_property("pronouns", [
        "ps", "po", "pp", "pr", "pq", "psc", "poc", "ppc", "prc", "pqc"
    ])
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

    new_player.parents.add(player, containers)
    new_player.owner = new_player
    new_player.save()

    root.get_verb("accept").delete()

    bootstrap.load_verbs(repo, "moo.bootstrap.default_verbs")
    sys.gender_utils.set(player, "plural")
