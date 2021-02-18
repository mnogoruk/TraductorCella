import logging

from .models import Operator

logger = logging.getLogger(__name__)


class Operators:

    @classmethod
    def get_operator(cls, user):

        if isinstance(user, Operator):
            return user
        if user is None:
            operator = Operator.get_system_operator()
        elif user.is_anonymous:
            operator = Operator.get_anonymous_operator()
        else:
            operator = Operator.get_user_operator(user)
        return operator
