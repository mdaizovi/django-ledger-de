from django.conf import settings

from django_ledger import __version__
from django_ledger.settings import DJANGO_LEDGER_THEME
from contextvars import ContextVar
from contextlib import contextmanager

from django_ledger.settings import DJANGO_LEDGER_DB_ROUTER_HINT_KEY, DJANGO_LEDGER_DB_ATOMIC_ALIAS

DJL_CONTEXT_ACTION = ContextVar(DJANGO_LEDGER_DB_ROUTER_HINT_KEY, default=DJANGO_LEDGER_DB_ATOMIC_ALIAS)
DJL_ACTION_COA_CONFIGURE = 'coa_configure'


def django_ledger_context(request):
    return {
        'DEBUG': settings.DEBUG,
        'VERSION': __version__,
        'DJANGO_LEDGER_THEME': DJANGO_LEDGER_THEME,
    }


@contextmanager
def djl_action(action):
    """Bind a router action for the current task.

    Parameters
    ----------
    action : str
        Router action name.
    """
    token = DJL_CONTEXT_ACTION.set(action)
    try:
        yield
    finally:
        DJL_CONTEXT_ACTION.reset(token)
