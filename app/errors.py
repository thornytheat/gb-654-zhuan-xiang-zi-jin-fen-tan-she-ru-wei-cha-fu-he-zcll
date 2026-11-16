from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class DomainError(ValueError):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)

def install(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return JSONResponse(status_code=422, content={"error": exc.code, "message": exc.message})
