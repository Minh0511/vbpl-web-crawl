from app.helper.enum import ObjectNotFoundType


class CommonException(Exception):
    code: int
    message: str

    def __init__(self, code: int = None, message: str = None):
        self.code = code
        self.message = message

    def __str__(self):
        return str(self.message)


class ObjectNotFound(CommonException):
    def __init__(self, obj: ObjectNotFoundType):
        super().__init__(code=404, message=f"{obj.value} not found")
