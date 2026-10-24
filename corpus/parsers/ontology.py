"""Разбор экспорта базы знаний INCEpTION (RDF/XML) в плоский список тегов.

Не зависит от Django — можно запускать и тестировать отдельно.
"""
import xml.etree.ElementTree as ET

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
INCEPTION_NS = "http://www.ukp.informatik.tu-darmstadt.de/inception/1.0#"


def parse_ontology(path):
    """Возвращает список словарей:
    uri, label_ru, label_en, symbol, comment_ru, parent_uri, instance_of_uri
    Берутся только концепты из пространства INCEpTION (свойства rdf/rdfs пропускаются).
    """
    root = ET.parse(path).getroot()
    out = []
    for d in root:
        uri = d.get(RDF + "about")
        if not uri or not uri.startswith(INCEPTION_NS):
            continue
        labels, comments = {}, {}
        parent = instance_of = None
        is_property = False
        for el in d:
            if el.tag == RDFS + "label":
                labels[el.get(XML_LANG)] = (el.text or "").strip()
            elif el.tag == RDFS + "comment":
                comments[el.get(XML_LANG)] = (el.text or "").strip()
            elif el.tag == RDFS + "subClassOf":
                parent = el.get(RDF + "resource")
            elif el.tag == RDF + "type":
                res = el.get(RDF + "resource") or ""
                if res.endswith("#Property"):
                    is_property = True
                elif res != OWL_CLASS and res.startswith(INCEPTION_NS):
                    instance_of = res          # индивид (экземпляр) класса
        if is_property:
            continue                            # например, latex_formula
        out.append(dict(
            uri=uri,
            label_ru=labels.get("ru", ""),
            label_en=labels.get("en", ""),
            symbol=labels.get("symbol", ""),
            comment_ru=comments.get("ru", ""),
            parent_uri=parent,
            instance_of_uri=instance_of,
        ))
    return out
