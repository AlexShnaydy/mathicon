"""Разбор UIMA CAS XMI (экспорт INCEpTION) в обычные словари Python.

Не зависит от Django. Слои, которые читаем:
  Sentence, Token (+Lemma, POS, MorphologicalFeatures), Dependency/ROOT,
  webanno.custom.Math_entities (math_tag, Name, reference, args, specifier).
"""
import xml.etree.ElementTree as ET

XMI_ID = "{http://www.omg.org/XMI}id"


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _ids(value):
    return value.split() if value else []


def parse_xmi(path):
    root = ET.parse(path).getroot()
    by_type, by_id = {}, {}
    for el in root:
        t = _local(el.tag)
        by_type.setdefault(t, []).append(el)
        if el.get(XMI_ID):
            by_id[el.get(XMI_ID)] = el

    sofa = by_type["Sofa"][0]
    text = sofa.get("sofaString") or ""

    meta = {}
    if "DocumentMetaData" in by_type:
        m = by_type["DocumentMetaData"][0]
        meta = {k: m.get(k) for k in
                ("documentTitle", "documentId", "documentUri", "collectionId")}

    # ---- токены -----------------------------------------------------------
    tokens = []
    for el in sorted(by_type.get("Token", []), key=lambda e: int(e.get("begin"))):
        lem = by_id.get(el.get("lemma"))
        pos = by_id.get(el.get("pos"))
        mor = by_id.get(el.get("morph"))
        morph, morph_str = {}, ""
        if mor is not None:
            morph_str = mor.get("value", "")
            for pair in morph_str.split("|"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    morph[k] = v
        tokens.append(dict(
            xmi_id=el.get(XMI_ID),
            begin=int(el.get("begin")), end=int(el.get("end")),
            form=text[int(el.get("begin")):int(el.get("end"))],
            lemma=lem.get("value", "") if lem is not None else "",
            pos=(pos.get("coarseValue") or pos.get("PosValue") or "") if pos is not None else "",
            morph=morph, morph_str=morph_str,
            dep_rel="", head_xmi_id=None,
        ))
    tok_by_xmi = {t["xmi_id"]: t for t in tokens}

    # ---- зависимости ------------------------------------------------------
    n_deps = 0
    for el in by_type.get("Dependency", []) + by_type.get("ROOT", []):
        dep = tok_by_xmi.get(el.get("Dependent"))
        if dep is None:
            continue
        dep["dep_rel"] = el.get("DependencyType", "")
        gov = el.get("Governor")
        dep["head_xmi_id"] = None if gov == el.get("Dependent") else gov
        n_deps += 1

    # ---- предложения ------------------------------------------------------
    sentences = []
    for i, el in enumerate(sorted(by_type.get("Sentence", []),
                                  key=lambda e: int(e.get("begin")))):
        b, e = int(el.get("begin")), int(el.get("end"))
        sentences.append(dict(index=i, begin=b, end=e, content=text[b:e]))
    for t in tokens:
        for s in sentences:
            if s["begin"] <= t["begin"] and t["end"] <= s["end"]:
                t["sentence_index"] = s["index"]
                break

    # ---- математическая разметка -----------------------------------------
    def links(el, attr):
        res = []
        for ref in _ids(el.get(attr)):
            ln = by_id.get(ref)
            if ln is not None:
                res.append(dict(role=ln.get("role", ""), target_xmi_id=ln.get("target")))
        return res

    math = []
    for el in by_type.get("Math_entities", []):
        b, e = int(el.get("begin")), int(el.get("end"))
        math.append(dict(
            xmi_id=el.get(XMI_ID), begin=b, end=e, surface=text[b:e],
            tag_uri=el.get("math_tag"), name=el.get("Name", ""),
            reference=el.get("reference", ""),
            args=links(el, "args"), specifiers=links(el, "specifier"),
        ))

    return dict(text=text, meta=meta, sentences=sentences, tokens=tokens,
                math=math, n_deps=n_deps)
