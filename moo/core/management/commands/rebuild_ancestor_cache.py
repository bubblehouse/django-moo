"""
Management command to rebuild the AncestorCache table from scratch.

Use this after bulk Relationship changes, data migrations, or to recover from
a signal failure that left the cache inconsistent.
"""

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django_cte import with_cte

from moo.core.code import ContextManager
from moo.core.models.object import (
    AncestorCache,
    Object,
    _make_ancestors_cte,
)


class Command(BaseCommand):
    help = "Rebuild the AncestorCache table from scratch using the current Relationship data."

    def handle(self, *args, **options):
        self.stdout.write("Clearing existing AncestorCache rows...")
        deleted, _ = AncestorCache.objects.all().delete()
        self.stdout.write(f"  Deleted {deleted} rows.")

        # The CTE join uses Object._default_manager (SiteManager), which filters
        # by the active site. Iterate per-site so each pass sees its own site's
        # objects — parents never cross site boundaries, so this is correct.
        rows = []
        processed = 0
        for site in Site.objects.all():
            ContextManager.set_site(site)
            site_pks = list(Object.objects.values_list("id", flat=True))
            self.stdout.write(f"Rebuilding cache for site {site.domain!r}: {len(site_pks)} objects")
            for pk in site_pks:
                ancestors_cte = _make_ancestors_cte(pk)
                seen = {}
                for row in with_cte(
                    ancestors_cte,
                    select=ancestors_cte.join(Object, id=ancestors_cte.col.object_id)
                    .annotate(depth=ancestors_cte.col.depth, path_weight=ancestors_cte.col.path_weight)
                    .order_by("depth", "-path_weight"),
                ).values("id", "depth", "path_weight"):
                    if row["id"] not in seen:
                        seen[row["id"]] = row
                for row in seen.values():
                    rows.append(
                        AncestorCache(
                            descendant_id=pk,
                            ancestor_id=row["id"],
                            depth=row["depth"],
                            path_weight=row["path_weight"],
                        )
                    )
                processed += 1
                if len(rows) >= 500:
                    AncestorCache.objects.bulk_create(rows, ignore_conflicts=True)
                    rows = []

        if rows:
            AncestorCache.objects.bulk_create(rows, ignore_conflicts=True)

        total = AncestorCache.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"Done. Processed {processed} objects, created {total} AncestorCache rows.")
        )
