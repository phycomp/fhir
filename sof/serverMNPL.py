"""
使用streamlit fastapi tornado 開發IG 規範符合smart on fhir, FHIR specification ballot2 的 fhir server
構建一個符合 FHIR Implementation Guide (IG)、SMART on FHIR 和 FHIR Specification Ballot 2 規範的 FHIR Server，可以結合 FastAPI、Tornado 和 Streamlit 來完成。這裡的目標是：

FastAPI：用於構建核心 FHIR API，處理 SMART on FHIR 規範的認證和授權。
Tornado：為 FastAPI 提供非同步和高效能的服務器運行支持。
Streamlit：建立用於展示和測試 FHIR 資源的簡單前端。
以下是詳細的分步流程，逐步實現一個符合上述規範的 FHIR 服務器。

步驟 1：建立 FastAPI 應用程序以實現 FHIR 和 SMART on FHIR 規範
首先，設計一個基本的 FHIR Server，支持 Patient 資源的 CRUD 操作和符合 SMART on FHIR 的 OAuth 2.0 認證。

安裝依賴
pip install fastapi pydantic[dotenv] uvicorn tornado streamlit authlib
"""

#步驟 2：使用 Tornado 部署 FastAPI 應用 Tornado 可以作為一個高效能的 ASGI 服務器，將 FastAPI 應用部署在 Tornado 上：

# tornado_server.py
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from fastapi import FastAPI
from auth import app as fastapi_app
from fastapi.middleware.wsgi import WSGIMiddleware

class FastAPIHandler(RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._asgi_handler = WSGIMiddleware(fastapi_app)

    async def get(self):
        await self._asgi_handler(self.request)

if __name__ == "__main__":
    app = Application([
        (r"/.*", FastAPIHandler),
    ])
    app.listen(8000)
    tornado.ioloop.IOLoop.current().start()
