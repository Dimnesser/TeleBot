"""Фабрики callback_data для инлайн-кнопок."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MainMenuCB(CallbackData, prefix="menu"):
    section: str


class DepositTabCB(CallbackData, prefix="dtab"):
    category: str  # brainrot | hirsy | stars


class DepositQtyCB(CallbackData, prefix="dqty"):
    item_id: int
    delta: int  # +1 или -1


class DepositSortCB(CallbackData, prefix="dsort"):
    direction: str  # asc | desc


class DepositBuffCB(CallbackData, prefix="dbuff"):
    pass


class DepositSearchCB(CallbackData, prefix="dsearch"):
    pass


class DepositResetFiltersCB(CallbackData, prefix="dreset"):
    pass


class DepositNextCB(CallbackData, prefix="dnext"):
    pass


class DepositCloseCB(CallbackData, prefix="dclose"):
    pass


class DepositConfirmCB(CallbackData, prefix="dconfirm"):
    action: str  # send | cancel


class DepositQueueCB(CallbackData, prefix="dqueue"):
    action: str  # join | close


class DepositAdminCB(CallbackData, prefix="dadmin"):
    request_id: int
    action: str  # approve | reject


class StarsSkipPromoCB(CallbackData, prefix="stars_skip"):
    pass


class StarsCreateInvoiceCB(CallbackData, prefix="stars_inv"):
    pass
