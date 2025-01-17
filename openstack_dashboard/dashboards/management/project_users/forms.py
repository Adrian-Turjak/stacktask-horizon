# Copyright (c) 2014 Catalyst IT Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from horizon import forms
from horizon import messages
from horizon import exceptions

from openstack_dashboard.contrib.stacktask import api
from openstack_dashboard.dashboards.management import stacktask_util


def get_role_choices(request):
    """
    Returns a list of sorted 2-ary tuples containing
    the roles the current user can manage.
    """
    role_names = api.stacktask.valid_role_names_get(request)
    role_tuples = [(r, stacktask_util.get_role_text(r)) for r in role_names]
    role_tuples = sorted(role_tuples, key=lambda role: role[1])
    return role_tuples


class InviteUserForm(forms.SelfHandlingForm):
    email = forms.EmailField()
    roles = forms.MultipleChoiceField(label=_("Roles"),
                                      required=True,
                                      widget=forms.CheckboxSelectMultiple(),
                                      help_text=_("Select roles to grant to "
                                                  "the user within the "
                                                  "current project."))

    def __init__(self, *args, **kwargs):
        super(InviteUserForm, self).__init__(*args, **kwargs)
        self.fields['roles'].choices = get_role_choices(self.request)
        self.fields['roles'].initial = ['_member_']

    def handle(self, request, data):
        try:
            response = api.stacktask.user_invite(request, data)
            if response.status_code == 200:
                messages.success(request, _('Invited user successfully.'))
            else:
                messages.error(request, _('Failed to invite user.'))
            return True
        except Exception:
            messages.error(request, _('Failed to invite user.'))
            return False


class UpdateUserForm(forms.SelfHandlingForm):
    id = forms.Field()
    id.widget = forms.HiddenInput()
    name = forms.CharField()
    name.widget.attrs['readonly'] = True

    roles = forms.MultipleChoiceField(
        label=_("Roles"),
        required=True,
        widget=forms.CheckboxSelectMultiple(),
        help_text=_("Select roles to limit the "
                    "permission of the user.")
    )

    def __init__(self, *args, **kwargs):
        super(UpdateUserForm, self).__init__(*args, **kwargs)
        self.fields['roles'].choices = get_role_choices(self.request)

    def handle(self, request, data):
        # Get the before and after role lists, make two lists:
        # roles_added and roles_removed.
        # Submit each list to the api (add first?)
        try:
            user_id = data['id']
            current_user = api.stacktask.user_get(request, user_id)
            current_roles = set(current_user['roles'])
            managable_roles = set(
                api.stacktask.valid_role_names_get(request))
            current_managable_roles = current_roles & managable_roles
            desired_roles = set(data['roles'])
            roles_added = list(desired_roles - current_managable_roles)
            roles_removed = list(current_managable_roles - desired_roles)

            # Remove roles from user
            remove_status = 200
            if len(roles_removed) > 0:
                remove_response = api.stacktask.user_roles_remove(
                    request,
                    user_id,
                    roles_removed)
                remove_status = remove_response.status_code
            if remove_status != 200:
                messages.error(request, _('Failed to remove roles from user.'))
                return False

            # Add new roles
            added_status = 200
            if len(roles_added) > 0:
                added_response = api.stacktask.user_roles_add(
                    request,
                    user_id,
                    roles_added)
                added_status = added_response.status_code
            if added_status != 200:
                messages.error(request, _('Failed to add roles to user.'))
                return False

        except Exception:
            msg = _('Failed to update user.')
            url = reverse('horizon:management:project_users:index')
            exceptions.handle(request, msg, redirect=url)
            return False

        messages.success(request, _('Updated user successfully.'))
        return True
