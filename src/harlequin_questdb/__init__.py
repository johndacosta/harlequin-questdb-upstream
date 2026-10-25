from harlequin_questdb.adapter import QuestDBAdapter, QuestDBConnection, QuestDBCursor
from harlequin_questdb.cli_options import QUESTDB_OPTIONS

# Names used by the 0.4 staging tree. The published class remains QuestDBAdapter.
HarlequinQuestDbAdapter = QuestDBAdapter
HarlequinQuestDbConnection = QuestDBConnection
HarlequinQuestDbCursor = QuestDBCursor
QuestDBAdapter_OPTIONS = QUESTDB_OPTIONS

__all__ = [
    "HarlequinQuestDbAdapter",
    "HarlequinQuestDbConnection",
    "HarlequinQuestDbCursor",
    "QUESTDB_OPTIONS",
    "QuestDBAdapter",
    "QuestDBAdapter_OPTIONS",
    "QuestDBConnection",
    "QuestDBCursor",
]
