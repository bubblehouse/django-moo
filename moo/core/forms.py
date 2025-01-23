# -*- coding: utf-8 -*-
"""
Custom Django forms used in Admin interface.
"""

from django import forms
from django_ace import AceWidget

from .models import verb


class VerbAdminForm(forms.ModelForm):
    class Meta:
        model = verb.Verb
        fields = "__all__"
        widgets = {
            "code": AceWidget(
                mode="python",
                theme="solarized_dark",
                wordwrap=False,
                width="1000px",
                height="600px",
                minlines=None,
                maxlines=None,
                showprintmargin=False,
                showinvisibles=False,
                usesofttabs=True,
                tabsize=4,
                fontsize=None,
                toolbar=True,
                readonly=False,
                showgutter=True,
                behaviours=True,
            )
        }
