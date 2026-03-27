"""
Views for the web terminal interface.

The terminal view serves the xterm.js terminal page via Django templates.
The connect view proxies SSH connection setup to the internal webssh service,
so the browser never directly accesses the webssh POST endpoint.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from allauth.account.views import SignupView as AllauthSignupView
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render


class SignupView(AllauthSignupView):
    """Allauth signup view that allows already-authenticated users to register.

    Allauth normally redirects authenticated users away from the signup page.
    This subclass logs them out first so they can create a new account without
    needing to log out manually.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            auth_logout(request)
        return super().dispatch(request, *args, **kwargs)


def terminal(request):
    if request.method == "GET":
        context = {
            "username": request.user.username if request.user.is_authenticated else "",
            "hostname": settings.WEBSSH_HOSTNAME,
            "port": settings.WEBSSH_PORT,
        }
        return render(request, "shell/terminal.html", context)

    if request.method == "POST":
        data = {k: v for k, v in request.POST.items() if k != "csrfmiddlewaretoken"}
        encoded = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(settings.WEBSSH_INTERNAL_URL + "/", data=encoded)
        client_ip = request.headers.get("x-forwarded-for", request.META["REMOTE_ADDR"])
        req.add_header("X-Real-IP", client_ip)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return JsonResponse(json.loads(resp.read()), status=resp.status)
        except urllib.error.HTTPError as e:
            return JsonResponse(json.loads(e.read()), status=e.code)
        except OSError:
            return JsonResponse({"status": "webssh unreachable"}, status=502)

    return HttpResponseNotAllowed(["GET", "POST"])
