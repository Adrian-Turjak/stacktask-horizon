# Copyright (c) 2015 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from django.conf import settings
from django import http
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon.utils import functions as utils

from openstack_dashboard.contrib.stacktask.content.token \
    import forms as token_forms
from openstack_dashboard.contrib.stacktask import api


def _logout_msg_response(request, msg):
    response = http.HttpResponseRedirect(settings.LOGOUT_URL)
    utils.add_logout_reason(request, response, msg)
    return response


def _logout_msg_response_success(request, msg):
    response = _logout_msg_response(request, msg)
    response.set_cookie('logout_reason_class', 'success', max_age=10)
    return response


def submit_token_router(request, *args, **kwargs):
    """
    A router function that ensures the correct view gets
    the request for any token, based on its type.
    """
    # Get details of the token
    token_uuid = kwargs['token']
    token = api.stacktask.token_get(request, token_uuid, {})
    if not token or token.status_code != 200:
        msg = _("Invalid token. Please request another.")
        return _logout_msg_response(request, msg)

    json = token.json()
    if 'password' in json['required_fields']:
        return SubmitTokenPasswordView.as_view()(request, *args, **kwargs)
    elif 'confirm' in json['required_fields']:
        return SubmitTokenConfirmView.as_view()(request, *args, **kwargs)

    return _logout_msg_response(request, _("Unsupported token type."))


class SubmitTokenPasswordView(forms.ModalFormView):
    form_class = token_forms.PasswordForm
    template_name = 'stacktask/token/setpassword.html'

    def get(self, request, *args, **kwargs):
        sc = super(SubmitTokenPasswordView, self)
        return sc.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        sc = super(SubmitTokenPasswordView, self)
        return sc.post(request, *args, **kwargs)

    def form_valid(self, form):
        # All form data has been validated and POSTed.
        # We can now submit the token for processing along with parameters.
        # All codepaths here return a Redirect response.
        parameters = {
            'password': form.cleaned_data['new_password']
        }
        token_uuid = self.kwargs['token']
        token_response = api.stacktask.token_submit(form.request,
                                                    token_uuid,
                                                    parameters)

        if token_response.ok:
            msg = _("Password successfully set. Please log in to continue.")
            return _logout_msg_response_success(form.request, msg)

        msg = (_("Token form submission failed. Response code %(code)s.") %
               {'code': token_response.status_code})
        return _logout_msg_response(form.request, msg)

    def get_context_data(self, **kwargs):
        sc = super(SubmitTokenPasswordView, self)
        context = sc.get_context_data(**kwargs)
        try:
            context['token'] = self.kwargs['token']
        except Exception:
            exceptions.handle(self.request)
        return context


class SubmitTokenConfirmView(forms.ModalFormView):
    form_class = token_forms.ConfirmForm
    template_name = 'stacktask/token/tokenconfirm.html'

    def get(self, request, *args, **kwargs):
        sc = super(SubmitTokenConfirmView, self)
        return sc.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        sc = super(SubmitTokenConfirmView, self)
        return sc.post(request, *args, **kwargs)

    def form_valid(self, form):
        token_uuid = self.kwargs['token']
        parameters = {
            'confirm': True
        }
        token_response = api.stacktask.token_submit(form.request,
                                                    token_uuid,
                                                    parameters)

        if token_response.ok:
            msg = _("Welcome to the project! Please log in to continue.")
            return _logout_msg_response_success(form.request, msg)

        msg = (_("Invitation accept form submission failed. Response code %(code)s.") %
               {'code': token_response.status_code})
        return _logout_msg_response(form.request, msg)

    def get_context_data(self, **kwargs):
        sc = super(SubmitTokenConfirmView, self)
        context = sc.get_context_data(**kwargs)
        try:
            context['token'] = self.kwargs['token']
        except Exception:
            exceptions.handle(self.request)
        return context
