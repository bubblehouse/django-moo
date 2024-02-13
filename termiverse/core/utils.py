import logging

log = logging.getLogger(__name__)

def apply_default_permissions(instance):
    from .models import Object
    from .models.verb import AccessibleVerb
    set_default_permissions = AccessibleVerb.objects.filter(
        origin = Object.objects.get(pk=1),
        names__name = 'set_default_permissions'
    )
    if set_default_permissions:
        set_default_permissions[0](instance)
    else:
        log.warning(f"set_default_permissions failed for {instance}: verb not found")
