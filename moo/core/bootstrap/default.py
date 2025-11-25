import logging

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
    root.add_verb("accept", code="return True")
    root.set_property("description", "The root class from which all objects inherit.", inherited=True)
    root.set_property("key", None, inherited=True)

    rooms = create("Generic Room", parents=[root], location=None)
    rooms.set_property("description", "There's not much to see here.", inherited=True)
    rooms.set_property("exits", {}, inherited=True)
    mail_room = create("Mail Distribution Center", parents=[rooms], location=None)

    player = create("Generic Player", parents=[root], location=None)
    programmers = create("Generic Programmer", parents=[player], location=None)
    wizards = create("Generic Wizard", parents=[programmers], location=None)
    wizard.parents.add(wizards)

    thing = create("Generic Thing", parents=[root], location=None)
    containers.parents.add(thing)

    door = create("Generic Exit", location=None)
    door.set_property("open", False, inherited=True)
    door.set_property("locked", False, inherited=True)
    door.set_property("autolock", False, inherited=True)

    notes = create("Generic Note", parents=[thing], location=None)
    letters = create("Generic Letter", parents=[notes], location=None)

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
