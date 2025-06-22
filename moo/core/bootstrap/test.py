import logging

from moo.core import bootstrap, code, create, lookup

log = logging.getLogger(__name__)

repo = bootstrap.initialize_dataset("test")
wizard = lookup("Wizard")
containers = lookup("container class")

with code.context(wizard, log.info):
    bag = create("bag of holding", parents=[containers], location=wizard)
    hammer = create("wizard hammer", location=bag)
    book = create("class book", parents=[containers], location=bag)
    players = create("player class", location=book)
    guests = create("guest class", location=book)
    guests.parents.add(players)
    authors = create("author class", location=book)
    authors.parents.add(players)
    programmers = create("programmer class", location=book)
    programmers.parents.add(authors)
    wizards = create("wizard class", location=book)
    wizards.parents.add(programmers)

    wizard.parents.add(wizards)

    rooms = create("room class", parents=[containers], location=book)
    rooms.set_property("description", "There's not much to see here.", inherited=True)

    lab = create("The Laboratory")
    lab.parents.add(rooms)
    lab.set_property(
        "description",
        """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""",
    )

    wizard.location = lab
    wizard.save()

    player = create(name="Player", unique_name=True, location=lab)

    bootstrap.load_verbs(repo, "moo.core.bootstrap.test_verbs")
