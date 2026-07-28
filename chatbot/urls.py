from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("menu/", views.menu_page, name="menu"),
    path("contact/", views.contact_page, name="contact"),
    path("api/chat/", views.chat_api, name="chat_api"),
]
