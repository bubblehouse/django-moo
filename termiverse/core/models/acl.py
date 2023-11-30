import logging

from .. import code

log = logging.getLogger(__name__)

class AccessibleMixin(object):
    """
    The base class for all Objects, Verbs, and Properties.
    """
    def get_type(self):
        return self.__class__.__name__

    def check_permission(self, permission, subject):
        """
        Check if the current caller has permission for something.
        """
        caller = code.get_caller()
        if not caller:
            return
        if permission == 'grant' and caller.owns(subject):
            return
        caller.is_allowed(permission, subject, fatal=True)

    def allow(self, accessor, permission, create=False):
        """
        Allow a certain object or group to do something on this object.

        [ACL] allowed to grant on this (or owner of this)
        """
        self.check_permission('grant', self)
        if isinstance(accessor, str):
            # it's an group
            pass
        else:
            # it's an object
            pass

    def deny(self, accessor, permission, create=False):
        """
        Deny a certain object or group from doing something on this object.

        [ACL] allowed to grant on this (or owner of this)
        """
        self.check_permission('grant', self)
        if isinstance(accessor, str):
            # it's an group
            pass
        else:
            # it's an object
            pass
