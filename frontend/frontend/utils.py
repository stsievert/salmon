from fastapi import HTTPException


class ServerException(HTTPException):
    def __init__(self, msg):
        raise HTTPException(status_code=500, detail=msg)
