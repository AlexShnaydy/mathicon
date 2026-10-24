import os

from django.core.management.base import BaseCommand, CommandError

from corpus.importer import ImportProblem, import_xmi_file


class Command(BaseCommand):
    help = "Импорт документа из UIMA CAS XMI (экспорт INCEpTION)"

    def add_arguments(self, parser):
        parser.add_argument("xmi_file")
        parser.add_argument("--title", help="Название текста (по умолчанию из метаданных XMI)")
        parser.add_argument("--replace", action="store_true",
                            help="Заменить текст, если он уже загружен")

    def handle(self, xmi_file, title=None, replace=False, **opts):
        try:
            with open(xmi_file, "rb") as f:
                text, st = import_xmi_file(f, title=title, replace=replace,
                                           source_name=os.path.basename(xmi_file))
        except ImportProblem as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(
            f"«{text.title}»: предложений {st['sentences']}, токенов {st['tokens']}, "
            f"мат. аннотаций {st['annotations']}"))
        if st["stub_tags"]:
            self.stdout.write(self.style.WARNING(
                f"Тегов, которых нет в онтологии: {st['stub_tags']} (сначала импортируйте math.rdf)"))