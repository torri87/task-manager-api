import enum


class TaskStatus(enum.StrEnum):
    BACKLOG = 'Backlog'
    IN_PROGRESS = 'In Progress'
    REVIEW = 'Review'
    DONE = 'Done'
    CANCELLED = 'Cancelled'


class TaskPriority(enum.StrEnum):
    LOW = 'Low'
    MEDIUM = 'Medium'
    HIGH = 'High'


ACTIVE_STATUSES = (TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW)
FINAL_STATUSES = (TaskStatus.DONE, TaskStatus.CANCELLED)


class TaskSortField(enum.StrEnum):
    CREATED_AT = 'created_at'
    DEADLINE = 'deadline'
    PRIORITY = 'priority'


class SortOrder(enum.StrEnum):
    ASC = 'asc'
    DESC = 'desc'