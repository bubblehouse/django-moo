# pylint: disable=undefined-variable
lab, _ = bootstrap.get_or_create_object("The Laboratory", unique_name=True, parents=[rooms])
lab.set_property(
    "description",
    """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""",
)
sys.set_property("player_start", lab)

agency, _ = bootstrap.get_or_create_object("The Agency", unique_name=True, parents=[rooms])
agency.set_property(
    "description",
    """A quiet back room where the Tradesmen gather between assignments.
    Clipboards, blueprints, and half-finished notes cover every surface.""",
)
sys.set_property("agency", agency)

neighborhood, _ = bootstrap.get_or_create_object("The Neighborhood", unique_name=True, parents=[rooms])
neighborhood.set_property(
    "description",
    """A quiet residential street corner, pleasant enough in a vague way.
    A couple of wrought-iron garden chairs sit near a low stone wall.
    The kind of place where nothing happens, loudly.""",
)
sys.set_property("neighborhood", neighborhood)

if wizard.location != lab:
    wizard.location = lab
    wizard.save()
