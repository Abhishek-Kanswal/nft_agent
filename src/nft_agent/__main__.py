# filepath: \\wsl.localhost\Ubuntu\home\abhishekopisop\visionai-agent\agents\nft_agent\src\nft_agent\__main__.py
import asyncio
import logging
import os
from aiohttp import web
from dotenv import load_dotenv
from types import SimpleNamespace

from .nft_agent import NFTPortfolioAgent
from sentient_agent_framework import Session, Query, ResponseHandler  # framework types

load_dotenv()
logger = logging.getLogger("nft_agent")
logging.basicConfig(level=logging.INFO)

agent = NFTPortfolioAgent()

async def assist_handler(request: web.Request):
    payload = await request.json()
    # Session and Query in the framework are Protocols and may not be instantiable.
    # Use a simple object that satisfies the expected attributes instead.
    session = SimpleNamespace(id=payload.get("session", {}).get("id", "http-session"))
    query = SimpleNamespace(prompt=payload.get("query", {}).get("prompt", ""))

    class SimpleResponseHandler(ResponseHandler):
        def __init__(self, aioresp):
            self._resp = aioresp

        async def emit_text_block(self, name: str, text: str):
            await self._resp.write(f"{name}: {text}\n".encode())

        async def emit_json(self, name: str, data):
            import json
            await self._resp.write(f"{name}: ".encode() + json.dumps(data, default=str).encode() + b"\n")

        async def complete(self):
            await self._resp.write(b"COMPLETE\n")
            await self._resp.drain()
            await self._resp.write_eof()

    # streamed response
    resp = web.StreamResponse(status=200, reason='OK', headers={"Content-Type": "text/plain; charset=utf-8"})
    await resp.prepare(request)
    handler = SimpleResponseHandler(resp)
    await agent.assist(session, query, handler)
    return resp

def main():
    port = int(os.getenv("NFT_AGENT_PORT", "8003"))
    app = web.Application()
    app.router.add_post("/agent/nft_agent/assist", assist_handler)
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()