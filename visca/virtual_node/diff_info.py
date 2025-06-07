from enum import Enum


class DiffType(Enum):
    DELETED = 'Deleted'
    ADDED = 'Added'
    UPDATED = 'Updated'
    SAME = 'Same'


class DiffInfo:
    def __init__(
        self,
        diff_type: DiffType
    ):
        self.diff_type = diff_type
