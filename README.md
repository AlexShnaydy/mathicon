# Математикон — прототип БД и сайта

Django + SQLite (по умолчанию) или PostgreSQL.

## Запуск
```
pip install -r requirements.txt
python manage.py makemigrations corpus
python manage.py migrate
python manage.py import_ontology data/math.rdf
python manage.py import_xmi data/formula_vklyucheniy.xmi --title "Формула включений и исключений"
python manage.py createsuperuser
python manage.py runserver
```
Откройте http://127.0.0.1:8000/ (поиск, список текстов) и /admin/ (интерфейс для хостов).

## PostgreSQL
Задайте переменные окружения `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` — и повторите migrate/import.

## Структура
- `corpus/parsers/` — разбор XMI и RDF (чистый Python, без Django).
- `corpus/models.py` — Tag, Text, Sentence, Token, MathAnnotation, MathRelation.
- `corpus/management/commands/` — import_ontology, import_xmi.
