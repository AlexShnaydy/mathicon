from django.urls import path
from . import views

urlpatterns = [
    path("", views.search, name="search"),
    path("texts/", views.text_list, name="text_list"),
    path("texts/<int:pk>/", views.text_detail, name="text_detail"),
    path("ontology/", views.ontology, name="ontology"),
]
