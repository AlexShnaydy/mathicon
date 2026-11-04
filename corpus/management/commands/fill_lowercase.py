from django.core.cache import cache
from django.core.management.base import BaseCommand

from corpus.models import MathAnnotation, Token
from corpus.search import OPTIONS_KEY, lc


def _fill(model, mapping, size=2000):
    """mapping: {поле_с_нижним_регистром: исходное_поле}. Идём по кускам по pk."""
    last, total = 0, 0
    while True:
        chunk = list(model.objects.filter(pk__gt=last).order_by("pk")[:size])
        if not chunk:
            return total
        for obj in chunk:
            for lower_field, src in mapping.items():
                setattr(obj, lower_field, lc(getattr(obj, src)))
        model.objects.bulk_update(chunk, list(mapping))
        last = chunk[-1].pk
        total += len(chunk)


class Command(BaseCommand):
    help = "Заполнить поля с нижним регистром у уже загруженных текстов (нужно один раз после обновления)"

    def handle(self, *args, **opts):
        n1 = _fill(Token, {"form_lower": "form", "lemma_lower": "lemma"})
        n2 = _fill(MathAnnotation, {"surface_lower": "surface"})
        cache.delete(OPTIONS_KEY)
        self.stdout.write(self.style.SUCCESS(f"Токенов обновлено: {n1}, аннотаций: {n2}"))