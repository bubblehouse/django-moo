import logging
import secrets
from time import time

from django.contrib.auth import get_user_model

from moo import bootstrap
from moo.core import code, lookup
from moo.core.models import Player
from moo.core.models.acl import Access, Permission

log = logging.getLogger(__name__)
User = get_user_model()

repo = bootstrap.initialize_dataset("default")
wizard = lookup("Wizard")

with code.ContextManager(wizard, log.info):
    sys = lookup(1)

    # LambdaMOO special sentinel references (mirrors $nothing, $ambiguous_match, $failed_match)
    sys.set_property("nothing", lookup("nothing"))
    sys.set_property("ambiguous_match", lookup("ambiguous_match"))
    sys.set_property("failed_match", lookup("failed_match"))

    containers, containers_created = bootstrap.get_or_create_object("Generic Container", unique_name=True)
    if containers_created:
        containers.add_verb("accept", code="return True")
    containers.owner = wizard
    containers.save()
    sys.set_property("container", containers)
    containers.set_property("open_key", None)
    containers.set_property("open", False, inherit_owner=True)
    containers.set_property("opaque", False, inherit_owner=True)

    root, root_created = bootstrap.get_or_create_object("Root Class", unique_name=True)
    if root_created:
        root.add_verb("accept", code="return True")
    sys.set_property("root_class", root)
    root.set_property("description", "")
    root.set_property("key", None)

    rooms, _ = bootstrap.get_or_create_object("Generic Room", unique_name=True, parents=[root])
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

    mail_room, _ = bootstrap.get_or_create_object("Mail Distribution Center", unique_name=True, parents=[rooms])

    player, _ = bootstrap.get_or_create_object("Generic Player", unique_name=True, parents=[root])
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
    player.set_property("wrap_column", "auto")
    player.set_property("object_gaglist", [])
    player.set_property("page_absent_msg", "%n is not currently logged in.")
    player.set_property("page_origin_msg", "You sense that %n is looking for you in %x(location).")
    player.set_property("page_echo_msg", "Your message has been sent.")
    player.set_property("whereis_location_msg", "%N is in %x(location).")
    player.set_property("who_location_msg", "%x(location)")
    player.set_property("victim_ejection_msg", "You have been ejected from %s by %s.")

    programmers, _ = bootstrap.get_or_create_object("Generic Programmer", unique_name=True, parents=[player])
    sys.set_property("programmer", programmers)
    wizards, _ = bootstrap.get_or_create_object("Generic Wizard", unique_name=True, parents=[programmers])
    sys.set_property("wizard", wizards)
    if not wizard.parents.filter(pk=wizards.pk).exists():
        wizard.parents.add(wizards)

    thing, _ = bootstrap.get_or_create_object("Generic Thing", unique_name=True, parents=[root])
    sys.set_property("thing", thing)
    thing.set_property("otake_succeeded_msg", "%N picks up %t.")
    thing.set_property("otake_failed_msg", "")
    thing.set_property("take_succeeded_msg", "You take %t.")
    thing.set_property("take_failed_msg", "You can't pick that up.")
    thing.set_property("odrop_succeeded_msg", "%N drops %t.")
    thing.set_property("odrop_failed_msg", "%N tries to drop %t but fails!")
    thing.set_property("drop_succeeded_msg", "You drop %t.")
    thing.set_property("drop_failed_msg", "You can't seem to drop %t here.")
    if not containers.parents.filter(pk=thing.pk).exists():
        containers.parents.add(thing)

    furniture, _ = bootstrap.get_or_create_object("Generic Furniture", unique_name=True, parents=[thing])
    sys.set_property("furniture", furniture)
    furniture.set_property("take_failed_msg", "It's not possible to move something like this.")
    furniture.set_property("otake_failed_msg", "%N tries to pick up %t, but it won't budge.")
    furniture.set_property("sit_succeeded_msg", "You sit on %t.")
    furniture.set_property("osit_succeeded_msg", "%N sits on %t.")
    furniture.set_property("sit_failed_msg", "You are already sitting on %t.")
    furniture.set_property("stand_succeeded_msg", "You stand up from %t.")
    furniture.set_property("ostand_succeeded_msg", "%N stands up from %t.")
    furniture.set_property("stand_failed_msg", "You aren't sitting on %t.")

    exits, _ = bootstrap.get_or_create_object("Generic Exit", unique_name=True, parents=[root])
    sys.set_property("exit", exits)
    exits.set_property("source", None)
    exits.set_property("dest", None)
    exits.set_property("nogo_msg", "You can't go that way.")
    exits.set_property("onogo_msg", "{actor} can't go that way.")
    exits.set_property("arrive_msg", "You arrive at {subject}.")
    exits.set_property("oarrive_msg", "{actor} arrives at {subject}.")
    exits.set_property("oleave_msg", "{actor} leaves {subject}.")
    exits.set_property("leave_msg", "You leave {subject}.")

    notes, _ = bootstrap.get_or_create_object("Generic Note", unique_name=True, parents=[thing])
    sys.set_property("note", notes)
    notes.set_property("text", "")
    notes.set_property("read_key", None)

    letters, _ = bootstrap.get_or_create_object("Generic Letter", unique_name=True, parents=[notes])
    sys.set_property("letter", letters)

    lock_utils, _ = bootstrap.get_or_create_object("Lock Utilities", unique_name=True)
    sys.set_property("lock_utils", lock_utils)

    string_utils, _ = bootstrap.get_or_create_object("String Utilities", unique_name=True)
    sys.set_property("string_utils", string_utils)

    match_utils, _ = bootstrap.get_or_create_object("Match Utilities", unique_name=True)
    sys.set_property("match_utils", match_utils)

    gender_utils, _ = bootstrap.get_or_create_object("Gender Utilities", unique_name=True)
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

    new_player, new_player_created = bootstrap.get_or_create_object("Player", unique_name=True, location=lab)
    player_rec, _ = Player.objects.get_or_create(avatar=new_player)
    if new_player_created:
        new_player.parents.add(player)
        new_player.owner = new_player
        new_player.save()

    # The Tradesmen — autonomous builder agents
    # Mason ($player): digs rooms and wires exits
    mason_obj, _ = bootstrap.get_or_create_object("Mason", unique_name=True, parents=[player])
    mason_obj.owner = mason_obj
    mason_obj.set_property("home", agency)
    mason_obj.save()
    mason_user, mason_created = User.objects.get_or_create(username="mason")
    if mason_created:
        mason_user.set_password("Mxq7vB2nKpL4")
        mason_user.save()
    Player.objects.get_or_create(user=mason_user, defaults=dict(avatar=mason_obj))

    # Tinker ($programmer): writes verbs for interactive objects and secret exits
    tinker_obj, _ = bootstrap.get_or_create_object("Tinker", unique_name=True, parents=[programmers])
    tinker_obj.owner = tinker_obj
    tinker_obj.set_property("home", agency)
    tinker_obj.save()
    tinker_user, tinker_created = User.objects.get_or_create(username="tinker")
    if tinker_created:
        tinker_user.set_password("Pw9cX3mZrT6y")
        tinker_user.save()
    Player.objects.get_or_create(user=tinker_user, defaults=dict(avatar=tinker_obj))

    # Joiner ($player): creates furniture and containers
    joiner_obj, _ = bootstrap.get_or_create_object("Joiner", unique_name=True, parents=[player])
    joiner_obj.owner = joiner_obj
    joiner_obj.set_property("home", agency)
    joiner_obj.save()
    joiner_user, joiner_created = User.objects.get_or_create(username="joiner")
    if joiner_created:
        joiner_user.set_password("Hn4kD8sQvY2f")
        joiner_user.save()
    Player.objects.get_or_create(user=joiner_user, defaults=dict(avatar=joiner_obj))

    # Harbinger ($programmer): creates NPCs, uses @eval for random roll and tell verb
    harbinger_obj, _ = bootstrap.get_or_create_object("Harbinger", unique_name=True, parents=[programmers])
    harbinger_obj.owner = harbinger_obj
    harbinger_obj.set_property("home", agency)
    harbinger_obj.save()
    harbinger_user, harbinger_created = User.objects.get_or_create(username="harbinger")
    if harbinger_created:
        harbinger_user.set_password("Bt6wF5jRcU3e")
        harbinger_user.save()
    Player.objects.get_or_create(user=harbinger_user, defaults=dict(avatar=harbinger_obj))

    # Stocker ($programmer): consumable items, dispensing objects, and multi-use props
    stocker_obj, _ = bootstrap.get_or_create_object("Stocker", unique_name=True, parents=[programmers])
    stocker_obj.owner = stocker_obj
    stocker_obj.set_property("home", agency)
    stocker_obj.save()
    stocker_user, stocker_created = User.objects.get_or_create(username="stocker")
    if stocker_created:
        stocker_user.set_password("Vn5sL9eJwA7k")
        stocker_user.save()
    Player.objects.get_or_create(user=stocker_user, defaults=dict(avatar=stocker_obj))

    # Foreman ($player): orchestrates token chain, detects stalls, loops automatically
    foreman_obj, _ = bootstrap.get_or_create_object("Foreman", unique_name=True, parents=[player])
    foreman_obj.owner = foreman_obj
    foreman_obj.set_property("home", agency)
    foreman_obj.save()
    foreman_user, foreman_created = User.objects.get_or_create(username="foreman")
    if foreman_created:
        foreman_user.set_password("Jk2mR7nXpW5q")
        foreman_user.save()
    Player.objects.get_or_create(user=foreman_user, defaults=dict(avatar=foreman_obj))

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

    # The Inspectors — autonomous verb-testing agents (token chain via Foreman)
    # Quartermaster ($player): exercises container open/close/take/put/lock mechanics
    quartermaster_obj, _ = bootstrap.get_or_create_object("Quartermaster", unique_name=True, parents=[player])
    quartermaster_obj.owner = quartermaster_obj
    quartermaster_obj.set_property("home", agency)
    quartermaster_obj.save()
    quartermaster_user, quartermaster_created = User.objects.get_or_create(username="quartermaster")
    if quartermaster_created:
        quartermaster_user.set_password("Xp3nQ8vLmT2k")
        quartermaster_user.save()
    Player.objects.get_or_create(user=quartermaster_user, defaults=dict(avatar=quartermaster_obj))

    # Warden ($player): exercises exit locking, @lock/@unlock, key-based traversal
    warden_obj, _ = bootstrap.get_or_create_object("Warden", unique_name=True, parents=[player])
    warden_obj.owner = warden_obj
    warden_obj.set_property("home", agency)
    warden_obj.save()
    warden_user, warden_created = User.objects.get_or_create(username="warden")
    if warden_created:
        warden_user.set_password("Bz6wR4hNsY9j")
        warden_user.save()
    Player.objects.get_or_create(user=warden_user, defaults=dict(avatar=warden_obj))

    # Archivist ($player): exercises note/letter create, read, lock, erase, burn
    archivist_obj, _ = bootstrap.get_or_create_object("Archivist", unique_name=True, parents=[player])
    archivist_obj.owner = archivist_obj
    archivist_obj.set_property("home", agency)
    archivist_obj.save()
    archivist_user, archivist_created = User.objects.get_or_create(username="archivist")
    if archivist_created:
        archivist_user.set_password("Wr7mK5pDcF3n")
        archivist_user.save()
    Player.objects.get_or_create(user=archivist_user, defaults=dict(avatar=archivist_obj))

    # Tailor ($player): exercises @gender, pronoun substitution, @messages, @check
    tailor_obj, _ = bootstrap.get_or_create_object("Tailor", unique_name=True, parents=[player])
    tailor_obj.owner = tailor_obj
    tailor_obj.set_property("home", agency)
    tailor_obj.save()
    tailor_user, tailor_created = User.objects.get_or_create(username="tailor")
    if tailor_created:
        tailor_user.set_password("Gv2sM9xJnH6q")
        tailor_user.save()
    Player.objects.get_or_create(user=tailor_user, defaults=dict(avatar=tailor_obj))

    # The Neighbours — autonomous social-testing agents (timer-based, run simultaneously)
    # Gossip ($player): Mrs. Helen Lovejoy; emotes, whispers, exercises social output
    gossip_obj, _ = bootstrap.get_or_create_object("Gossip", unique_name=True, parents=[player])
    gossip_obj.owner = gossip_obj
    gossip_obj.set_property("home", neighborhood)
    gossip_obj.save()
    gossip_user, gossip_created = User.objects.get_or_create(username="gossip")
    if gossip_created:
        gossip_user.set_password("Lk4tN7wCqX1e")
        gossip_user.save()
    Player.objects.get_or_create(user=gossip_user, defaults=dict(avatar=gossip_obj))

    # Prude ($player): Mrs. Agnes Skinner; gag/ungag/paranoid cycles, social filtering
    prude_obj, _ = bootstrap.get_or_create_object("Prude", unique_name=True, parents=[player])
    prude_obj.owner = prude_obj
    prude_obj.set_property("home", neighborhood)
    prude_obj.save()
    prude_user, prude_created = User.objects.get_or_create(username="prude")
    if prude_created:
        prude_user.set_password("Fy8eP5rTbW3m")
        prude_user.save()
    Player.objects.get_or_create(user=prude_user, defaults=dict(avatar=prude_obj))

    # The Wanderer — autonomous world explorer (timer-based, runs indefinitely)
    # Cartographer ($programmers): surveys rooms, exercises @who/@whereis/@rooms/@audit
    cartographer_obj, _ = bootstrap.get_or_create_object("Cartographer", unique_name=True, parents=[programmers])
    cartographer_obj.owner = cartographer_obj
    cartographer_obj.set_property("home", lab)
    cartographer_obj.save()
    cartographer_user, cartographer_created = User.objects.get_or_create(username="cartographer")
    if cartographer_created:
        cartographer_user.set_password("Hc9vD2kRsM7p")
        cartographer_user.save()
    Player.objects.get_or_create(user=cartographer_user, defaults=dict(avatar=cartographer_obj))

    # Grant derive to everyone on all standard system classes so any player can
    # create instances via @create without needing wizard privileges.
    derive_perm = Permission.objects.get(name="derive")
    for _cls in [root, thing, rooms, exits, player, programmers, furniture, containers]:
        Access.objects.get_or_create(
            object=_cls,
            permission=derive_perm,
            type="group",
            group="everyone",
            rule="allow",
        )

    # Remove the temporary bootstrap accept verbs — verb files provide the real ones.
    if root.has_verb("accept"):
        root.get_verb("accept").delete()
    if containers.has_verb("accept"):
        containers.get_verb("accept").delete()
    bootstrap.load_verbs(repo, "moo.bootstrap.default_verbs", replace=True)
    sys.gender_utils.set(player, "plural")
    sys.set_property("gripe_recipients", [wizard])
