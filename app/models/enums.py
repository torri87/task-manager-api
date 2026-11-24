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