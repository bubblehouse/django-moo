import logging
from time import time

from moo.core import bootstrap, code, create, lookup

log = logging.getLogger(__name__)

repo = bootstrap.initialize_dataset("default")
wizard = lookup("Wizard")
containers = lookup("container class")
containers.name = "Generic Container"
containers.save()

with code.context(wizard, log.info):
    sys = lookup(1)
    sys.set_property("player_start", None)

    root = create("Root Class", location=None)
    sys.set_property("root_class", root)
    root.add_verb("accept", code="return True")
    root.set_property("description", "The root class from which all objects inherit.", inherited=True)
    root.set_property("key", None, inherited=True)

    rooms = create("Generic Room", parents=[root], location=None)
    sys.set_property("room", rooms)
    rooms.set_property("description", "There's not much to see here.", inherited=True)
    rooms.set_property("exits", {}, inherited=True)
    rooms.set_property("victim_ejection_message", "You have been ejected from %s by %s.", inherited=True)
    rooms.set_property("ejection_message", "You have ejected %s.", inherited=True)
    rooms.set_property("room_ejection_message", "%s has been ejected by %s.", inherited=True)
    rooms.set_property("residents", [], inherited=True)
    rooms.set_property("free_entry", True, inherited=True)
    rooms.set_property("entrances", {}, inherited=True)
    rooms.set_property("dark", False, inherited=True)
    rooms.set_property("content_list_type", 0, inherited=True)

    mail_room = create("Mail Distribution Center", parents=[rooms], location=None)

    player = create("Generic Player", parents=[root], location=None)
    sys.set_property("player", player)
    player.set_property("last_connect_time", time(), inherited=True)
    player.set_property("ownership_quota", 1000)
    player.set_property("gender", "neuter", inherited=True)
    player.set_property("ps", "it", inherited=True)
    player.set_property("po", "it", inherited=True)
    player.set_property("pp", "its", inherited=True)
    player.set_property("pr", "itself", inherited=True)
    player.set_property("pq", "its", inherited=True)
    player.set_property("psc", "It", inherited=True)
    player.set_property("poc", "It", inherited=True)
    player.set_property("ppc", "Its", inherited=True)
    player.set_property("prc", "Itself", inherited=True)
    player.set_property("pqc", "Its", inherited=True)
    player.set_property("home", None, inherited=True)
    player.set_property("gaglist", [], inherited=True)
    player.set_property("paranoid", False, inherited=True)
    player.set_property("responsible", [], inherited=True)
    player.set_property("lines", 10, inherited=True)
    player.set_property("object_gaglist", [], inherited=True)
    player.set_property("page_absent_msg", "%n is not currently logged in.", inherited=True)
    player.set_property("page_origin_msg", "You sense that %s is looking for you in %s.", inherited=True)
    player.set_property("page_echo_msg", "Your message has been sent.", inherited=True)
    player.set_property("whereis_location_msg", "%s is in %s.", inherited=True)
    player.set_property("who_location_msg", "%l", inherited=True)

    programmers = create("Generic Programmer", parents=[player], location=None)
    sys.set_property("programmer", programmers)
    wizards = create("Generic Wizard", parents=[programmers], location=None)
    sys.set_property("wizard", wizards)
    wizard.parents.add(wizards)

    thing = create("Generic Thing", parents=[root], location=None)
    sys.set_property("thing", thing)
    containers.parents.add(thing)

    door = create("Generic Exit", location=None)
    sys.set_property("exit", door)
    door.set_property("open", False, inherited=True)
    door.set_property("locked", False, inherited=True)
    door.set_property("autolock", False, inherited=True)

    notes = create("Generic Note", parents=[thing], location=None)
    sys.set_property("note", notes)
    letters = create("Generic Letter", parents=[notes], location=None)
    sys.set_property("letter", letters)

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
    new_player.parents.add(player, containers)

    root.get_verb("accept").delete()

    bootstrap.load_verbs(repo, "moo.core.bootstrap.default_verbs")
