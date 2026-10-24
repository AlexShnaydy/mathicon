from django.db import models


class Tag(models.Model):
    """Концепт онтологии математических тегов (из базы знаний INCEpTION)."""
    uri = models.CharField("URI в INCEpTION", max_length=255, unique=True)
    label_ru = models.CharField("Название (рус.)", max_length=255, blank=True)
    label_en = models.CharField("Название (англ.)", max_length=255, blank=True)
    symbol = models.CharField("Символ", max_length=255, blank=True)
    comment_ru = models.TextField("Описание", blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="children", verbose_name="Надкласс (subClassOf)")
    instance_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="instances", verbose_name="Экземпляр класса")

    class Meta:
        ordering = ["label_ru"]
        verbose_name = "тег онтологии"
        verbose_name_plural = "онтология тегов"

    def __str__(self):
        return self.label_ru or self.label_en or self.uri

    def descendant_ids(self):
        """id этого тега и всех его потомков (подклассы и экземпляры)."""
        seen, stack = {self.pk}, [self.pk]
        while stack:
            cur = stack.pop()
            kids = Tag.objects.filter(models.Q(parent_id=cur) | models.Q(instance_of_id=cur))
            for k in kids.values_list("pk", flat=True):
                if k not in seen:
                    seen.add(k)
                    stack.append(k)
        return seen


class Text(models.Model):
    title = models.CharField("Название", max_length=500)
    source_uri = models.CharField("Исходный файл", max_length=500, blank=True)
    collection = models.CharField("Коллекция/проект", max_length=255, blank=True)
    content = models.TextField("Текст")
    language = models.CharField("Язык", max_length=10, default="ru")
    metadata = models.JSONField("Метаданные", default=dict, blank=True,
                                help_text="Автор, источник, жанр, уровень, раздел математики и т.д.")
    ling_source = models.CharField("Лингвистическая разметка", max_length=10, default="auto",
                                   choices=[("auto", "автоматическая"), ("manual", "ручная")])
    math_source = models.CharField("Математическая разметка", max_length=10, default="manual",
                                   choices=[("auto", "автоматическая"), ("manual", "ручная")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "текст"
        verbose_name_plural = "тексты"

    def __str__(self):
        return self.title


class Sentence(models.Model):
    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="sentences")
    index = models.PositiveIntegerField()
    begin = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    content = models.TextField()

    class Meta:
        ordering = ["text", "index"]
        constraints = [models.UniqueConstraint(fields=["text", "index"], name="uniq_sentence")]

    def __str__(self):
        return f"{self.text_id}:{self.index} {self.content[:50]}"


class Token(models.Model):
    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="tokens")
    sentence = models.ForeignKey(Sentence, on_delete=models.CASCADE, related_name="tokens")
    index = models.PositiveIntegerField("Позиция в тексте")
    begin = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    form = models.CharField("Словоформа", max_length=255)
    lemma = models.CharField("Лемма", max_length=255, db_index=True)
    pos = models.CharField("Часть речи (UD)", max_length=16, db_index=True)
    morph = models.JSONField("Морфология", default=dict, blank=True)
    morph_str = models.CharField(max_length=255, blank=True)
    dep_rel = models.CharField("Синтаксическая связь", max_length=32, blank=True)
    head = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="dependents")

    class Meta:
        ordering = ["text", "index"]
        indexes = [models.Index(fields=["text", "index"])]
        constraints = [models.UniqueConstraint(fields=["text", "index"], name="uniq_token")]

    def __str__(self):
        return self.form


class MathAnnotation(models.Model):
    """Спан математической разметки (слой Math_entities в INCEpTION)."""
    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="math_annotations")
    begin = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    surface = models.CharField("Фрагмент", max_length=500)
    tag = models.ForeignKey(Tag, on_delete=models.PROTECT, related_name="annotations")
    name = models.CharField("Значение (Name)", max_length=255, blank=True)
    reference = models.CharField("Ссылка (reference)", max_length=255, blank=True)
    first_token = models.ForeignKey(Token, null=True, on_delete=models.SET_NULL, related_name="+")
    last_token = models.ForeignKey(Token, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["text", "begin"]
        indexes = [models.Index(fields=["tag"])]
        verbose_name = "математическая аннотация"
        verbose_name_plural = "математические аннотации"

    def __str__(self):
        return f"{self.surface} → {self.tag}"


class MathRelation(models.Model):
    """Связь между аннотациями: args / specifier (в текущих данных пока пусто)."""
    ARG, SPEC = "arg", "specifier"
    source = models.ForeignKey(MathAnnotation, on_delete=models.CASCADE, related_name="outgoing")
    target = models.ForeignKey(MathAnnotation, on_delete=models.CASCADE, related_name="incoming")
    kind = models.CharField(max_length=10, choices=[(ARG, "аргумент"), (SPEC, "уточнение")])
    role = models.CharField("Роль", max_length=255, blank=True)

    class Meta:
        verbose_name = "связь аннотаций"
        verbose_name_plural = "связи аннотаций"
