#1.1 配置 OAuth 2.0 認證 SMART on FHIR 使用 OAuth 2.0 來進行授權。我們將使用 Authlib 庫來實現一個基於 OAuth 的認證服務。

# auth.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
import os

app = FastAPI()

# 設置 OAuth2 的配置（可以通過環境變量或配置文件）
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "mysecret"))

oauth = OAuth(app)
oauth.register(
    name='fhir',
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    authorize_url="https://example.com/oauth2/authorize",
    access_token_url="https://example.com/oauth2/token",
    client_kwargs={"scope": "openid profile"}
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(authorizationUrl="https://example.com/oauth2/authorize")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = await oauth.fhir.parse_id_token(token)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid authentication")
    return user
