class HackMateException(Exception):
    """Base exception for all domain errors in HackMate."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProjectNotFoundError(HackMateException):
    def __init__(self, project_id: str):
        super().__init__(f"Project with ID '{project_id}' was not found.", status_code=404)


class SecurityViolationError(HackMateException):
    def __init__(self, detail: str):
        super().__init__(f"Security constraint violated: {detail}", status_code=403)


class InvalidStateTransitionError(HackMateException):
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition project from state '{current_status}' to '{target_status}'.",
            status_code=409,
        )


class RunnerUnavailableError(HackMateException):
    def __init__(self, reason: str):
        super().__init__(f"Execution runner is unavailable: {reason}", status_code=503)


class BuildExecutionError(HackMateException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)
