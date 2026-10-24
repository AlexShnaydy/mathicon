from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path

from .importer import ImportProblem, import_xmi_file
from .models import MathAnnotation, MathRelation, Sentence, Tag, Text, Token


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("label_ru", "label_en", "symbol", "parent", "instance_of")
    search_fields = ("label_ru", "label_en", "uri")
    autocomplete_fields = ("parent", "instance_of")


class MathAnnotationInline(admin.TabularInline):
    model = MathAnnotation
    extra = 0
    fields = ("surface", "tag", "name")
    readonly_fields = ("surface",)
    autocomplete_fields = ("tag",)
    show_change_link = True


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ("title", "collection", "ling_source", "math_source", "created_at")
    list_filter = ("collection", "ling_source", "math_source")
    search_fields = ("title",)
    inlines = [MathAnnotationInline]

    change_list_template = "admin/corpus/text/change_list.html"   # добавляет кнопку

    def get_urls(self):
        # адрес должен идти ПЕРЕД стандартными
        return [path("upload-xmi/", self.admin_site.admin_view(self.upload_view),
                     name="corpus_text_upload_xmi")] + super().get_urls()

    def upload_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == "POST":
            files = request.FILES.getlist("files")
            replace = bool(request.POST.get("replace"))
            title = request.POST.get("title", "").strip() if len(files) == 1 else ""
            if not files:
                messages.error(request, "Выберите хотя бы один файл.")
            for f in files:
                try:
                    text, st = import_xmi_file(f, title=title or None, replace=replace,
                                               source_name=f.name)
                except ImportProblem as e:
                    messages.error(request, f"{f.name}: {e}")
                    continue
                messages.success(request, f"{f.name}: загружен «{text.title}» — предложений "
                                 f"{st['sentences']}, токенов {st['tokens']}, "
                                 f"мат. аннотаций {st['annotations']}.")
                if st["stub_tags"]:
                    messages.warning(request, f"{f.name}: {st['stub_tags']} тег(ов) нет в онтологии "
                                     "— они сохранены без названий. Загрузите актуальный math.rdf.")
            return redirect("admin:corpus_text_changelist")
        ctx = dict(self.admin_site.each_context(request), title="Загрузка XMI",
                   opts=self.model._meta)
        return render(request, "admin/corpus/text/upload_xmi.html", ctx)


@admin.register(MathAnnotation)
class MathAnnotationAdmin(admin.ModelAdmin):
    list_display = ("surface", "tag", "name", "text")
    list_filter = ("tag",)
    search_fields = ("surface", "tag__label_ru")
    raw_id_fields = ("text", "first_token", "last_token")
    autocomplete_fields = ("tag",)


@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ("text", "index", "content")
    raw_id_fields = ("text",)
    search_fields = ("content",)


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("form", "lemma", "pos", "dep_rel", "text", "index")
    list_filter = ("pos", "dep_rel")
    search_fields = ("form", "lemma")
    raw_id_fields = ("text", "sentence", "head")


admin.site.register(MathRelation)
