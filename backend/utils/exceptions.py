"""全局异常处理与自定义异常类。

约定：所有业务错误抛出 AppException，由全局异常处理器统一返回
{"code":..., "message":..., "data":null}，不向客户端暴露堆栈信息。
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    """自定义业务异常，携带 code / message / data。"""

    def __init__(self, code: int = 400, message: str = "error", data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器。"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        # 返回与 code 一致的 HTTP 状态码，便于前端区分
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "data": exc.data},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        # Pydantic 参数校验失败 -> 400
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "参数校验失败", "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        # 兜底：任何未捕获异常都返回 500，且不暴露堆栈
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )
