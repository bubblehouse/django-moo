import logging
from time import time

from moo.core import bootstrap, code, create, lookup
from moo.core.models import Player, User

log = logging.getLogger(__name__)

repo = bootstrap.initialize_dataset("default")
wizard = lookup("Wizard")
user = User.objects.create(username="wizard")
Player.objects.create(user=user, avatar=wizard, wizard=True)

containers = lookup("container class")
containers.name = "Generic Container"
containers.save()

with code.context(wizard, log.info):
    sys = lookup(1)
    sys.set_property("player_start", None)
    sys.set_property("container", containers)

    root = create("Root Class", location=None)
    sys.set_property("root_class", root)
    root.add_verb("accept", code="return True")
    root.set_property("description", "The root class from which all objects inherit.", inherit_owner=True)
    root.set_property("key", None, inherit_owner=True)

    rooms = create("Generic Room", parents=[root], location=None)
    sys.set_property("room", rooms)
    rooms.set_property("blessed_object", None, inherit_owner=True)
    rooms.set_property("blessed_task_id", None, inherit_owner=True)
    rooms.set_property("description", "There's not much to see here.", inherit_owner=True)
    rooms.set_property("exits", [], inherit_owner=True)
    rooms.set_property("victim_ejection_message", "You have been ejected from %s by %s.", inherit_owner=True)
    rooms.set_property("ejection_message", "You have ejected %s.", inherit_owner=True)
    rooms.set_property("room_ejection_message", "%s has been ejected by %s.", inherit_owner=True)
    rooms.set_property("residents", [], inherit_owner=True)
    rooms.set_property("free_entry", True, inherit_owner=True)
    rooms.set_property("entrances", [], inherit_owner=True)
    rooms.set_property("dark", False, inherit_owner=True)
    rooms.set_property("content_list_type", 0, inherit_owner=True)

    mail_room = create("Mail Distribution Center", parents=[rooms], location=None)

    player = create("Generic Player", parents=[root], location=None)
    sys.set_property("player", player)
    player.set_property("last_connect_time", time(), inherit_owner=True)
    player.set_property("ownership_quota", 1000)
    player.set_property("gender", "neuter", inherit_owner=True)
    player.set_property("ps", "it", inherit_owner=True)
    player.set_property("po", "it", inherit_owner=True)
    player.set_property("pp", "its", inherit_owner=True)
    player.set_property("pr", "itself", inherit_owner=True)
    player.set_property("pq", "its", inherit_owner=True)
    player.set_property("psc", "It", inherit_owner=True)
    player.set_property("poc", "It", inherit_owner=True)
    player.set_property("ppc", "Its", inherit_owner=True)
    player.set_property("prc", "Itself", inherit_owner=True)
    player.set_property("pqc", "Its", inherit_owner=True)
    player.set_property("home", None, inherit_owner=True)
    player.set_property("gaglist", [], inherit_owner=True)
    player.set_property("paranoid", False, inherit_owner=True)
    player.set_property("responsible", [], inherit_owner=True)
    player.set_property("lines", 10, inherit_owner=True)
    player.set_property("object_gaglist", [], inherit_owner=True)
    player.set_property("page_absent_msg", "%n is not currently logged in.", inherit_owner=True)
    player.set_property("page_origin_msg", "You sense that %s is looking for you in %s.", inherit_owner=True)
    player.set_property("page_echo_msg", "Your message has been sent.", inherit_owner=True)
    player.set_property("whereis_location_msg", "%s is in %s.", inherit_owner=True)
    player.set_property("who_location_msg", "%l", inherit_owner=True)

    programmers = create("Generic Programmer", parents=[player], location=None)
    sys.set_property("programmer", programmers)
    wizards = create("Generic Wizard", parents=[programmers], location=None)
    sys.set_property("wizard", wizards)
    wizard.parents.add(wizards)

    thing = create("Generic Thing", parents=[root], location=None)
    sys.set_property("thing", thing)
    containers.parents.add(thing)

    exits = create("Generic Exit", parents=[root], location=None)
    sys.set_property("exit", exits)
    exits.set_property("open", False, inherit_owner=True)
    exits.set_property("locked", False, inherit_owner=True)
    exits.set_property("autolock", False, inherit_owner=True)

    exits.set_property("source", None, inherit_owner=True)
    exits.set_property("dest", None, inherit_owner=True)
    exits.set_property("nogo_msg", "You can't go that way.", inherit_owner=True)
    exits.set_property("onogo_msg", "{actor} can't go that way.", inherit_owner=True)
    exits.set_property("arrive_msg", "You arrive at {subject}.", inherit_owner=True)
    exits.set_property("oarrive_msg", "{actor} arrives at {subject}.", inherit_owner=True)
    exits.set_property("oleave_msg", "{actor} leaves {subject}.", inherit_owner=True)
    exits.set_property("leave_msg", "You leave {subject}.", inherit_owner=True)

    notes = create("Generic Note", parents=[thing], location=None)
    sys.set_property("note", notes)
    letters = create("Generic Letter", parents=[notes], location=None)
    sys.set_property("letter", letters)

    lock_utils = create("Lock Utilities", parents=[notes], location=None)
    sys.set_property("lock_utils", lock_utils)

    lab = create("The Laboratory", parents=[rooms], location=None)
    lab.set_property(
        "description",
        """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""",
    )

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

    bootstrap.load_verbs(repo, "moo.core.bootstrap.default_verbs")
