import logging

from moo.core import bootstrap, code
from moo.core import create, lookup

log = logging.getLogger(__name__)

repo = bootstrap.initialize_dataset('default')
wizard = lookup('Wizard')
containers = lookup('containers class')

with code.context(wizard, log.info):
    bag = create('bag of holding', parents=[containers], location=wizard)
    hammer = create('wizard hammer', location=bag)
    players = create('player class', location=bag)

    rooms = create('room class', parents=[containers], location=bag)
    rooms.set_property("description", "There's not much to see here.", inherited=True)

    lab = create('The Laboratory', parents=[rooms])
    lab.set_property("description", """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""")

    wizard.location = lab
    wizard.save()

    bootstrap.load_verbs(repo, dataset='default')
