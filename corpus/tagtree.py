"""Построение дерева тегов для выпадающего списка и страницы онтологии."""
from collections import defaultdict

from django.db.models import Count

from .models import Tag


def _name(t):
    return (t.label_ru or t.label_en or t.uri).casefold()


def build_nodes(tags):
    """tags: объекты с pk, parent_id, instance_of_id, own (число аннотаций у самого тега),
    label_ru, label_en, uri. Возвращает плоский список узлов в порядке обхода в глубину.
    total — число аннотаций у тега и всех его потомков."""
    children = defaultdict(list)
    for t in tags:
        children[t.parent_id or t.instance_of_id].append(t)
    for lst in children.values():
        lst.sort(key=_name)

    out, seen = [], set()

    def walk(t, depth):
        seen.add(t.pk)
        node = dict(tag=t, depth=depth, pad=depth * 24,
                    indent="\u00a0\u00a0\u00a0" * depth + ("– " if depth else ""),
                    own=t.own, total=t.own, is_instance=bool(t.instance_of_id))
        out.append(node)
        for c in children.get(t.pk, []):
            if c.pk not in seen:          # защита от циклов в иерархии
                node["total"] += walk(c, depth + 1)
        return node["total"]

    for r in children.get(None, []):
        if r.pk not in seen:
            walk(r, 0)
    return out


def build_tree():
    return build_nodes(list(Tag.objects.annotate(own=Count("annotations"))))