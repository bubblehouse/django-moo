# -*- coding: utf-8 -*-
"""
Custom allauth signup form for DjangoMOO.

Collects character name, gender, and description alongside the standard
allauth fields (username, email, password). After allauth creates the
Django User, save(user) creates the MOO Object avatar and links it via
a Player record.
"""

from django import forms

from moo.core import code, lookup
from moo.core.models import Player
from moo.sdk import create

GENDER_CHOICES = [
    ("neuter", "Neuter (it/its)"),
    ("male", "Male (he/him)"),
    ("female", "Female (she/her)"),
    ("plural", "Plural (they/them)"),
]


class SignupForm(forms.Form):
    character_name = forms.CharField(
        max_length=255,
        label="Character Name",
        help_text="The name others see in-game.",
    )
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        label="Gender",
        initial="plural",
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Description",
        required=False,
        help_text="How your character appears to others.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def signup(self, request, user):
        wizard = lookup("Wizard")
        sys = lookup("System Object")

        character_name = self.cleaned_data["character_name"]
        gender = self.cleaned_data["gender"]
        description = self.cleaned_data.get("description", "")

        with code.ContextManager(wizard, lambda msg: None):
            player_class = sys.get_property("player")
            start_location = sys.get_property("player_start")
            gender_utils = sys.get_property("gender_utils")

            avatar = create(character_name, parents=[player_class], location=start_location)
            avatar.owner = avatar
            avatar.save()

            gender_utils.invoke_verb("set", avatar, gender)

            if description:
                avatar.set_property("description", description)

            Player.objects.create(user=user, avatar=avatar)
