"""
Runtime registration of additional account roles from regional plugins.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

from django.utils.translation import gettext_lazy as _
from django_ledger.io import roles as roles_module

def register_extra_roles(
    asset_roles: Iterable[Tuple[str, str]] = (),
    liability_roles: Iterable[Tuple[str, str]] = (),
    equity_roles: Iterable[Tuple[str, str]] = (),
    income_roles: Iterable[Tuple[str, str]] = (),
    cogs_roles: Iterable[Tuple[str, str]] = (),
    expense_roles: Iterable[Tuple[str, str]] = (),
    group_memberships: dict | None = None,
) -> None:
    """
    Extend ``django_ledger.io.roles`` with country-specific roles at startup.

    Parameters
    ----------
    asset_roles, liability_roles, ...
        Iterables of ``(role_id, verbose_label)`` tuples.
    group_memberships:
        Mapping of ``GROUP_*`` constant names to lists of role ids, e.g.
        ``{'GROUP_CURRENT_ASSETS': ['asset_ca_vat_recv']}``.
    """

    category_map = [
        ('ASSET', asset_roles, 0, 0),
        ('LIABILITY', liability_roles, 1, 1),
        ('EQUITY', equity_roles, 2, 2), # aka capital aka dividends
        ('INCOME', income_roles, 2, 3), # aka revenue
        ('COGS', cogs_roles, 2, 4), # Cost of Goods Sold
        ('EXPENSE', expense_roles, 2, 5),
    ]

    def _append_role_choices(choices: list, index: int, items: List[Tuple[str, str]]) -> None:
        heading, role_choices = choices[index]
        choices[index] = (heading, role_choices + tuple(items))

    for category, role_items, choice_index, form_choice_index in category_map:
        new_roles: List[Tuple[str, str]] = [(r, _(label)) for r, label in role_items]
        if not new_roles:
            continue

        for role_id, label in new_roles:
            const_name = role_id.upper()
            setattr(roles_module, const_name, role_id)
            roles_module.VALID_ROLES.append(role_id)
            roles_module.BS_ROLES[role_id] = category
            roles_module.ACCOUNT_LIST_ROLE_ORDER.append(role_id)
            roles_module.ACCOUNT_LIST_ROLE_VERBOSE[role_id] = label

        _append_role_choices(roles_module.ACCOUNT_ROLE_CHOICES, choice_index, new_roles)
        if form_choice_index < len(roles_module.ACCOUNT_ROLE_CHOICES_FOR_FORMS):
            _append_role_choices(
                roles_module.ACCOUNT_ROLE_CHOICES_FOR_FORMS,
                form_choice_index,
                new_roles,
            )

        if choice_index == 0:
            roles_module.ROLES_ORDER_ASSETS.extend(role_id for role_id, _ in new_roles)
        elif choice_index == 1:
            roles_module.ROLES_ORDER_LIABILITIES.extend(role_id for role_id, _ in new_roles)
        elif choice_index == 2:
            roles_module.ROLES_ORDER_CAPITAL.extend(role_id for role_id, _ in new_roles)
        roles_module.ROLES_ORDER_ALL = (
            roles_module.ROLES_ORDER_ASSETS
            + roles_module.ROLES_ORDER_LIABILITIES
            + roles_module.ROLES_ORDER_CAPITAL
        )

        top_group_name = {
            'ASSET': 'GROUP_ASSETS',
            'LIABILITY': 'GROUP_LIABILITIES',
            'EQUITY': 'GROUP_CAPITAL',
            'INCOME': 'GROUP_INCOME',
            'COGS': 'GROUP_COGS',
            'EXPENSE': 'GROUP_EXPENSES',
        }.get(category)
        if top_group_name:
            top_group = getattr(roles_module, top_group_name)
            top_group.extend(role_id for role_id, _ in new_roles)
            top_group[:] = list(set(top_group))

    if group_memberships:
        subgroup_parents = {
            'GROUP_CURRENT_ASSETS': ('GROUP_ASSETS',),
            'GROUP_NON_CURRENT_ASSETS': ('GROUP_ASSETS',),
            'GROUP_QUICK_ASSETS': ('GROUP_ASSETS',),
            'GROUP_CURRENT_LIABILITIES': ('GROUP_LIABILITIES',),
            'GROUP_LT_LIABILITIES': ('GROUP_LIABILITIES',),
        }
        for group_name, role_ids in group_memberships.items():
            group = getattr(roles_module, group_name)
            group.extend(role_ids)
            group[:] = list(set(group))
            for parent_name in subgroup_parents.get(group_name, ()):
                parent = getattr(roles_module, parent_name)
                parent.extend(role_ids)
                parent[:] = list(set(parent))
