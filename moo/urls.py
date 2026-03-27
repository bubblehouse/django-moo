"""
URL configuration for moo project.

The ``urlpatterns`` list routes URLs to views.
See https://docs.djangoproject.com/en/stable/topics/http/urls/ for details.
"""

from django.contrib import admin
from django.urls import include, path

from moo.shell.views import SignupView, terminal

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", SignupView.as_view(), name="account_signup"),
    path("accounts/", include("allauth.urls")),
    path("", terminal, name="terminal"),
]
