class AppError(Exception):
    """Expected product error that should become a user-facing API response."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
