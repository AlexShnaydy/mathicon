from django.core.management.base import BaseCommand
from django.db import transaction

from corpus.models import Tag
from corpus.parsers.ontology import parse_ontology


class Command(BaseCommand):
    help = "Импорт онтологии тегов из RDF/XML-экспорта базы знаний INCEpTION"

    def add_arguments(self, parser):
        parser.add_argument("rdf_file")

    @transaction.atomic
    def handle(self, rdf_file, **opts):
        items = parse_ontology(rdf_file)
        by_uri = {}
        for it in items:        # проход 1: сами теги (идемпотентно)
            tag, _ = Tag.objects.update_or_create(uri=it["uri"], defaults=dict(
                label_ru=it["label_ru"], label_en=it["label_en"],
                symbol=it["symbol"], comment_ru=it["comment_ru"]))
            by_uri[it["uri"]] = tag
        for it in items:        # проход 2: иерархия
            tag = by_uri[it["uri"]]
            tag.parent = by_uri.get(it["parent_uri"])
            tag.instance_of = by_uri.get(it["instance_of_uri"])
            tag.save(update_fields=["parent", "instance_of"])
        self.stdout.write(self.style.SUCCESS(f"Тегов импортировано: {len(items)}"))
