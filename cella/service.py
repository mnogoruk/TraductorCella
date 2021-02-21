import logging
from cella.models import Operator

logger = logging.getLogger(__name__)


class Operators:

    @classmethod
    def get_operator(cls, user):

        if isinstance(user, Operator):
            return user
        elif isinstance(user, int):
            return Operator.objects.get(id=user)
        elif user is None:
            return Operator.get_system_operator()
        elif user.is_anonymous:
            return Operator.get_anonymous_operator()
        else:
            return Operator.get_user_operator(user)