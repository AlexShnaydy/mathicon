"""Поиск по корпусу: разбор параметров формы и построение запросов к базе.
Лексико-грамматические и математические условия можно комбинировать."""
import re

from django.core.cache import cache
from django.db.models import Exists, OuterRef, Q

from .models import MathAnnotation, Tag, Token
from .ud import FEATURE_ORDER, FEATURE_RU, pos_label, value_label

OPTIONS_KEY = "mathicon_search_options"
FEAT_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")   # защита: имя признака попадает в запрос


def lc(s):
    """Нижний регистр. Одна и та же функция при загрузке текстов и при поиске."""
    return (s or "").lower()


def _variants(raw):
    return [v.strip() for v in (raw or "").split("|") if v.strip()]


def _text_q(field, raw, exact, lower=False):
    """Условие по текстовому полю. Варианты через |; «полное совпадение» или «содержит».
    Для регистронезависимого поиска ищем в полях *_lower."""
    q = Q()
    for v in _variants(raw):
        v = lc(v) if lower else v
        q |= Q(**{f"{field}__{'exact' if exact else 'contains'}": v})
    return q


class Params:
    """Параметры поиска из строки запроса (GET)."""

    def __init__(self, get):
        self.submitted = "go" in get
        s = self.submitted
        # лексико-грамматическая часть
        self.form = get.get("form", "").strip()
        self.lemma = get.get("lemma", "").strip()
        self.pos = get.get("pos", "").strip()
        self.exact = ("exact" in get) if s else True          # по умолчанию — полное совпадение
        self.feats = {k[2:]: v for k, v in get.items()
                      if k.startswith("f_") and v and FEAT_KEY.match(k[2:])}
        # математическая часть (учитывается, только если стоит галочка math)
        self.math = "math" in get
        tag = get.get("tag", "")
        self.tag = int(tag) if tag.isdigit() else None
        self.sub = ("sub" in get) if (s and self.math) else True
        self.mname = get.get("mname", "").strip()
        self.msurface = get.get("msurface", "").strip()
        self.mexact = ("mexact" in get) if (s and self.math) else True

    @property
    def has_lex(self):
        return bool(self.form or self.lemma or self.pos or self.feats)

    @property
    def active(self):
        return self.has_lex or self.math


def lex_filter(p):
    q = (_text_q("form_lower", p.form, p.exact, lower=True)
         & _text_q("lemma_lower", p.lemma, p.exact, lower=True))
    if p.pos:
        q &= Q(pos=p.pos)
    for key, value in p.feats.items():
        q &= Q(**{f"morph__{key}": value})
    return q


def math_filter(p):
    q = Q()
    if p.tag:
        tag = Tag.objects.filter(pk=p.tag).first()
        ids = (tag.descendant_ids() if p.sub else {tag.pk}) if tag else []
        q &= Q(tag_id__in=ids)
    q &= _text_q("name", p.mname, p.mexact)                    # значение: регистр важен (n и N)
    q &= _text_q("surface_lower", p.msurface, p.mexact, lower=True)
    return q


def run_search(p):
    """Возвращает (queryset, kind).
    Есть лексико-грамматические условия → результаты это слова (kind='token');
      если включена математика, слово должно лежать внутри подходящей аннотации.
    Только математика → результаты это аннотации (kind='annotation')."""
    if p.has_lex:
        qs = Token.objects.filter(lex_filter(p)).select_related("text", "sentence")
        if p.math:
            qs = qs.filter(Exists(MathAnnotation.objects.filter(
                math_filter(p), text_id=OuterRef("text_id"),
                begin__lte=OuterRef("begin"), end__gte=OuterRef("end"))))
        return qs.order_by("text_id", "index"), "token"
    qs = (MathAnnotation.objects.filter(math_filter(p))
          .select_related("text", "tag", "first_token__sentence"))
    return qs.order_by("text_id", "begin"), "annotation"


def search_options():
    """Значения для выпадающих списков берём из самой базы (кэш на 10 минут)."""
    data = cache.get(OPTIONS_KEY)
    if data is not None:
        return data
    pos = {v for v in Token.objects.order_by().values_list("pos", flat=True).distinct() if v}
    feats = {}
    for ms in Token.objects.order_by().values_list("morph_str", flat=True).distinct():
        for pair in (ms or "").split("|"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if FEAT_KEY.match(k):
                    feats.setdefault(k, set()).add(v)
    ordered = ([k for k in FEATURE_ORDER if k in feats]
               + sorted(k for k in feats if k not in FEATURE_ORDER))
    data = dict(
        pos=[dict(value=v, label=pos_label(v)) for v in sorted(pos)],
        feats=[dict(key=k, label=FEATURE_RU.get(k, k),
                    values=[dict(value=v, label=value_label(k, v)) for v in sorted(feats[k])])
               for k in ordered],
    )
    cache.set(OPTIONS_KEY, data, 600)
    return data