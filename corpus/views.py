from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import MathAnnotation, Tag, Text, Token
from .tagtree import build_tree

MAX_RESULTS = 200


def highlight(content, offset, spans):
    """Экранирует content и оборачивает спаны в <mark>.
    spans: [(begin, end, title)] в абсолютных символьных позициях текста;
    offset: абсолютная позиция начала content."""
    out, pos = [], 0
    for b, e, title in sorted(spans):
        b, e = b - offset, e - offset
        if b < pos or e > len(content):
            continue                    # пересечения/выход за границы пока пропускаем
        out.append(escape(content[pos:b]))
        out.append(f'<mark title="{escape(title)}">{escape(content[b:e])}</mark>')
        pos = e
    out.append(escape(content[pos:]))
    return mark_safe("".join(out))


def search(request):
    tag_id = request.GET.get("tag") or ""
    lemma = (request.GET.get("lemma") or "").strip()
    pos = (request.GET.get("pos") or "").strip().upper()
    results, total = [], 0

    if tag_id.isdigit():
        tag = get_object_or_404(Tag, pk=tag_id)
        qs = (MathAnnotation.objects.filter(tag_id__in=tag.descendant_ids())
              .select_related("text", "tag", "first_token__sentence"))
        total = qs.count()
        for a in qs[:MAX_RESULTS]:
            s = a.first_token.sentence if a.first_token else None
            html = (highlight(s.content, s.begin, [(a.begin, a.end, str(a.tag))])
                    if s else escape(a.surface))
            results.append(dict(text=a.text, html=html, note=str(a.tag)))
    elif lemma or pos:
        qs = Token.objects.select_related("text", "sentence")
        if lemma:
            qs = qs.filter(lemma__iexact=lemma)
        if pos:
            qs = qs.filter(pos=pos)
        total = qs.count()
        for t in qs[:MAX_RESULTS]:
            html = highlight(t.sentence.content, t.sentence.begin,
                             [(t.begin, t.end, f"{t.lemma} · {t.pos}")])
            results.append(dict(text=t.text, html=html, note=f"{t.lemma} · {t.pos}"))

    nodes = [n for n in build_tree() if n["total"] > 0]
    return render(request, "corpus/search.html", dict(
        nodes=nodes, results=results, total=total, shown=len(results),
        tag_id=tag_id, lemma=lemma, pos=pos,
        searched=bool(tag_id.isdigit() or lemma or pos)))


def text_list(request):
    return render(request, "corpus/text_list.html", dict(
        texts=Text.objects.annotate(n_tokens=Count("tokens", distinct=True),
                                    n_math=Count("math_annotations", distinct=True))))


def text_detail(request, pk):
    text = get_object_or_404(Text, pk=pk)
    anns = list(text.math_annotations.select_related("tag"))
    sentences = []
    for s in text.sentences.all():
        spans = [(a.begin, a.end, str(a.tag)) for a in anns
                 if a.begin >= s.begin and a.end <= s.end]
        sentences.append(highlight(s.content, s.begin, spans))
    return render(request, "corpus/text_detail.html",
                  dict(text=text, sentences=sentences, n_ann=len(anns)))

def ontology(request):
    return render(request, "corpus/ontology.html", dict(nodes=build_tree()))