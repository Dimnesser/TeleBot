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


class CasesCategoryCB(CallbackData, prefix="ccat"):
    category: str
    page: int = 0


class CaseOpenViewCB(CallbackData, prefix="cview"):
    case_id: int


class CaseQtySelectCB(CallbackData, prefix="cqty"):
    case_id: int
    qty: int


class CaseConfirmOpenCB(CallbackData, prefix="copen"):
    case_id: int
    qty: int


class CasesTopUpCB(CallbackData, prefix="ctopup"):
    pass


class CasesInventoryCB(CallbackData, prefix="cinv"):
    pass


class UpgraderHomeCB(CallbackData, prefix="uhome"):
    pass


class UpgraderMyItemsCB(CallbackData, prefix="umine"):
    page: int = 0


class UpgraderPickContributionCB(CallbackData, prefix="upick_c"):
    item_id: int


class UpgraderTargetsCB(CallbackData, prefix="utargets"):
    page: int = 0


class UpgraderPickTargetCB(CallbackData, prefix="upick_t"):
    index: int


class UpgraderPresetCB(CallbackData, prefix="upreset"):
    kind: str  # "mult" | "chance"
    value: int


class UpgraderConfirmCB(CallbackData, prefix="uconfirm"):
    pass


class UpgraderResetCB(CallbackData, prefix="ureset"):
    pass


class CrashHomeCB(CallbackData, prefix="chome"):
    pass


class CrashPickItemsCB(CallbackData, prefix="citems"):
    page: int = 0


class CrashPickItemCB(CallbackData, prefix="cpick"):
    item_id: int


class CrashStartCB(CallbackData, prefix="cstart"):
    pass


class CrashCashoutCB(CallbackData, prefix="ccashout"):
    pass


class DiceHomeCB(CallbackData, prefix="dhome"):
    pass


class DicePickItemsCB(CallbackData, prefix="ditems"):
    page: int = 0


class DicePickItemCB(CallbackData, prefix="dpick"):
    item_id: int


class DicePickColorCB(CallbackData, prefix="dcolor"):
    color: str


class DiceRollCB(CallbackData, prefix="droll"):
    pass


class DiceResetCB(CallbackData, prefix="dreset2"):
    pass
