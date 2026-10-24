from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Математикон — администрирование"
admin.site.site_title = "Математикон"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("corpus.urls")),
]
