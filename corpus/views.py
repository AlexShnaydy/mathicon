from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import MathAnnotation, Text
from .search import Params, run_search, search_options
from .tagtree import build_tree

PAGE_SIZE = 25


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


def _build_results(page, kind):
    results = []
    for obj in page.object_list:
        if kind == "token":
            s = obj.sentence
            note = f"{obj.lemma} · {obj.pos}" + (f" · {obj.morph_str}" if obj.morph_str else "")
            html = highlight(s.content, s.begin, [(obj.begin, obj.end, f"{obj.lemma} · {obj.pos}")])
            anns = MathAnnotation.objects.filter(
                text_id=obj.text_id, begin__lte=obj.begin, end__gte=obj.end).select_related("tag")
            math = [str(a.tag) + (f" = {a.name}" if a.name else "") for a in anns]
        else:
            s = obj.first_token.sentence if obj.first_token else None
            html = (highlight(s.content, s.begin, [(obj.begin, obj.end, str(obj.tag))])
                    if s else escape(obj.surface))
            note = ""
            math = [str(obj.tag) + (f" = {obj.name}" if obj.name else "")]
        results.append(dict(text=obj.text, html=html, note=note, math=math))
    return results


def search(request):
    p = Params(request.GET)
    page, kind, results = None, None, []
    if p.submitted and p.active:
        qs, kind = run_search(p)
        page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
        results = _build_results(page, kind)

    opts = search_options()
    feat_rows = [dict(f, selected=p.feats.get(f["key"], "")) for f in opts["feats"]]
    nodes = [n for n in build_tree() if n["total"] > 0]
    qs_params = request.GET.copy()
    qs_params.pop("page", None)
    return render(request, "corpus/search.html", dict(
        p=p, opts=opts, feat_rows=feat_rows, nodes=nodes,
        page=page, kind=kind, results=results, qs=qs_params.urlencode()))


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