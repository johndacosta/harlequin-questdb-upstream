from harlequin_questdb.adapter import (
    HarlequinQuestDbAdapter,
    HarlequinQuestDbConnection,
    HarlequinQuestDbCursor,
)
from harlequin_questdb.cli_options import QUESTDB_OPTIONS

# Public aliases for harlequin-questdb <=0.3.x (rhuygen/harlequin-questdb).
QuestDBAdapter = HarlequinQuestDbAdapter
QuestDBConnection = HarlequinQuestDbConnection
QuestDBCursor = HarlequinQuestDbCursor
QuestDBAdapter_OPTIONS = QUESTDB_OPTIONS

__all__ = [
    "HarlequinQuestDbAdapter",
    "HarlequinQuestDbConnection",
    "HarlequinQuestDbCursor",
    "QuestDBAdapter",
    "QuestDBConnection",
    "QuestDBCursor",
    "QUESTDB_OPTIONS",
    "QuestDBAdapter_OPTIONS",
]
