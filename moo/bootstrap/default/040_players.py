# pylint: disable=undefined-variable
new_player, new_player_created = bootstrap.get_or_create_object("Player", unique_name=True, location=lab)
player_rec, _ = Player.objects.get_or_create(avatar=new_player)
if new_player_created:
    new_player.parents.add(player)
    new_player.owner = new_player
    new_player.save()
