"""Импорт одного документа из XMI (INCEpTION) в базу.
Используется командой import_xmi и кнопкой «Загрузить XMI» в админке."""
import xml.etree.ElementTree as ET

from django.db import transaction

from .models import MathAnnotation, MathRelation, Sentence, Tag, Text, Token
from .parsers.xmi import parse_xmi


class ImportProblem(Exception):
    """Причина, по которой документ не загружен."""


def _default_title(meta, source_name):
    name = meta.get("documentTitle") or source_name or "Без названия"
    for ext in (".xmi", ".xml", ".conllu", ".txt"):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return name


@transaction.atomic
def import_xmi_file(source, title=None, replace=False, source_name=""):
    """source — путь к файлу или открытый файл (в т.ч. загруженный через сайт).
    Возвращает (Text, статистика). При проблеме бросает ImportProblem,
    и в базе ничего не остаётся."""
    try:
        d = parse_xmi(source)
    except (ET.ParseError, KeyError, IndexError):
        raise ImportProblem("файл не похож на XMI из INCEpTION (не найден текст документа)")

    meta = d["meta"]
    source_uri = meta.get("documentUri") or source_name
    if Text.objects.filter(source_uri=source_uri).exists():
        if not replace:
            raise ImportProblem("этот документ уже загружен (включите «Заменить, если уже загружен»)")
        Text.objects.filter(source_uri=source_uri).delete()

    text = Text.objects.create(
        title=title or _default_title(meta, source_name),
        source_uri=source_uri, collection=meta.get("collectionId") or "",
        content=d["text"], metadata={"inception": meta})

    sents = {s["index"]: Sentence.objects.create(text=text, **s) for s in d["sentences"]}

    toks = []
    for i, t in enumerate(d["tokens"]):
        toks.append(Token(text=text, sentence=sents[t["sentence_index"]], index=i,
                          begin=t["begin"], end=t["end"], form=t["form"], lemma=t["lemma"],
                          pos=t["pos"], morph=t["morph"], morph_str=t["morph_str"],
                          dep_rel=t["dep_rel"]))
    Token.objects.bulk_create(toks)

    toks = list(Token.objects.filter(text=text).order_by("index"))
    by_xmi = {t["xmi_id"]: obj for t, obj in zip(d["tokens"], toks)}
    for t, obj in zip(d["tokens"], toks):
        if t["head_xmi_id"]:
            obj.head = by_xmi[t["head_xmi_id"]]
    Token.objects.bulk_update(toks, ["head"])

    tags = {t.uri: t for t in Tag.objects.all()}
    stubs = 0
    anns = {}
    for m in d["math"]:
        tag = tags.get(m["tag_uri"])
        if tag is None:   # тега нет в онтологии — создаём заглушку, чтобы не потерять разметку
            tag = tags[m["tag_uri"]] = Tag.objects.create(uri=m["tag_uri"], label_ru=m["tag_uri"])
            stubs += 1
        inside = [t for t in toks if t.begin >= m["begin"] and t.end <= m["end"]]
        anns[m["xmi_id"]] = MathAnnotation.objects.create(
            text=text, begin=m["begin"], end=m["end"], surface=m["surface"], tag=tag,
            name=m["name"], reference=m["reference"],
            first_token=inside[0] if inside else None,
            last_token=inside[-1] if inside else None)
    for m in d["math"]:
        for kind, key in ((MathRelation.ARG, "args"), (MathRelation.SPEC, "specifiers")):
            for link in m[key]:
                target = anns.get(link["target_xmi_id"])
                if target:
                    MathRelation.objects.create(source=anns[m["xmi_id"]], target=target,
                                                kind=kind, role=link["role"])

    return text, dict(sentences=len(sents), tokens=len(toks),
                      annotations=len(anns), stub_tags=stubs)