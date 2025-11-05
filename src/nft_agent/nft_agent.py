# filepath: \\wsl.localhost\Ubuntu\home\abhishekopisop\visionai-agent\agents\nft_agent\src\nft_agent\nft_agent.py
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

import aiohttp
from dotenv import load_dotenv

from sentient_agent_framework import AbstractAgent, Session, Query, ResponseHandler
from .models.model_provider import ModelProvider

load_dotenv()
logger = logging.getLogger(__name__)

# Chains we'll query (Alchemy NFT API endpoints)
CHAIN_ENDPOINTS = {
    "ethereum": "https://eth-mainnet.g.alchemy.com/nft/v3",
    "polygon": "https://polygon-mainnet.g.alchemy.com/nft/v3",
    "arbitrum": "https://arb-mainnet.g.alchemy.com/nft/v3",
    "optimism": "https://opt-mainnet.g.alchemy.com/nft/v3",
    "base": "https://base-mainnet.g.alchemy.com/nft/v3",
}

OPENSEA_URL = "https://api.opensea.io/api/v2/chain"
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"


class NFTPortfolioAgent(AbstractAgent):
    """
    Agent that fetches an address's NFT portfolio (OpenSea + Alchemy) and produces
    a concise portfolio summary and optional AI-powered insights.
    """

    def __init__(self, name: str = "NFT Portfolio Agent"):
        super().__init__(name)
        self.model_provider = ModelProvider()
        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
        self.opensea_api_key = os.getenv("OPENSEA_API_KEY")
        logger.info(f"Initialized {name} (provider={self.model_provider.provider})")

    async def _fetch_opensea_nfts(self, chain: str, address: str) -> List[Dict[str, Any]]:
        url = f"{OPENSEA_URL}/{chain}/account/{address}/nfts"
        headers = {"accept": "application/json"}
        if self.opensea_api_key:
            headers["x-api-key"] = self.opensea_api_key

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning("OpenSea request failed %s %s", resp.status, text)
                        return []
                    data = await resp.json()
                    return data.get("nfts", [])
            except Exception as e:
                logger.warning("OpenSea fetch error: %s", e)
                return []

    async def _get_alchemy_floor(self, chain: str, contract: str) -> Dict[str, Any] | None:
        if not self.alchemy_api_key:
            return None
        base = CHAIN_ENDPOINTS.get(chain)
        if not base:
            return None
        url = f"{base}/{self.alchemy_api_key}/getFloorPrice?contractAddress={contract}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=12) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.json()
            except Exception as e:
                logger.debug("Alchemy floor fetch failed: %s", e)
                return None

    async def _get_eth_usd_price(self) -> float:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(COINGECKO_PRICE_URL, timeout=10) as resp:
                    if resp.status != 200:
                        return 0.0
                    data = await resp.json()
                    return float(data.get("ethereum", {}).get("usd", 0) or 0)
        except Exception:
            return 0.0

    def _build_prompt(self, wallet: str, portfolio: List[Dict[str, Any]], total_value_usd: float) -> str:
        lines = [f"Analyze NFT portfolio for wallet: {wallet}", f"Total estimated value USD: ${total_value_usd:.2f}", "", "Holdings:"]
        for p in portfolio[:25]:  # limit details
            lines.append(f"- {p.get('name','Unnamed')} | {p.get('contract')} | floor_usd=${p.get('floor_usd', 0):.2f} | chain={p.get('chain')}")
        lines.append("")
        lines.append("Provide a concise insight: 1-2 sentences summary, valuation confidence, and quick risks/opportunities.")
        return "\n".join(lines)

    async def assist(self, session: Session, query: Query, response_handler: ResponseHandler):
        wallet = query.prompt.strip()
        if not wallet:
            await response_handler.emit_text_block("ERROR", "No wallet address provided in query.prompt")
            await response_handler.complete()
            return

        await response_handler.emit_text_block("START", f"Analyzing NFT portfolio for {wallet}")

        eth_usd = await self._get_eth_usd_price()
        await response_handler.emit_text_block("PRICE", f"ETH/USD = {eth_usd:.2f}")

        all_holdings = []
        total_value_usd = 0.0

        # fetch per chain sequentially to keep things simple & avoid burst rate limits
        for chain in CHAIN_ENDPOINTS.keys():
            await response_handler.emit_text_block("FETCH_CHAIN", f"Fetching NFTs on {chain}...")
            nfts = await self._fetch_opensea_nfts(chain, wallet)
            await response_handler.emit_text_block("CHAIN_COUNT", f"{chain}: found {len(nfts)} NFTs")
            for nft in nfts:
                contract = nft.get("contract") or nft.get("contract_address") or nft.get("token_contract")
                name = nft.get("name", "Unnamed NFT")
                collection = nft.get("collection", {}).get("name") if isinstance(nft.get("collection"), dict) else nft.get("collection", "unknown")
                image = nft.get("image_url") or nft.get("image")
                opensea_url = nft.get("opensea_url") or nft.get("external_url") or ""
                floor_usd = 0.0
                price_data = await self._get_alchemy_floor(chain, contract) if contract else None
                if price_data:
                    # try to extract highest floor among marketplaces
                    best = 0.0
                    for market in ("openSea", "looksRare", "blur", "x2y2"):
                        m = price_data.get(market)
                        if isinstance(m, dict) and m.get("floorPrice") is not None:
                            try:
                                fp = float(m.get("floorPrice"))
                                best = max(best, fp)
                            except Exception:
                                continue
                    floor_eth = best
                    floor_usd = floor_eth * eth_usd
                total_value_usd += floor_usd
                all_holdings.append({
                    "chain": chain,
                    "name": name,
                    "collection": collection,
                    "contract": contract,
                    "image": image,
                    "opensea_url": opensea_url,
                    "floor_usd": floor_usd,
                })
                # polite pause
                await asyncio.sleep(0.2)

        await response_handler.emit_json("PORTFOLIO_SUMMARY", {"count": len(all_holdings), "estimated_value_usd": total_value_usd})

        # Build AI prompt and request insights
        prompt = self._build_prompt(wallet, all_holdings, total_value_usd)
        await response_handler.emit_text_block("AI_PROMPT", "Requesting AI summary...")

        try:
            analysis = ""
            # prefer streaming if available
            if hasattr(self.model_provider, "generate_stream"):
                async for chunk in self.model_provider.generate_stream(prompt):
                    analysis += chunk
                    await response_handler.emit_text_block("AI_CHUNK", chunk)
                    if len(analysis) > 600:
                        break
            else:
                analysis = await asyncio.wait_for(self.model_provider.generate(prompt), timeout=12.0)
            analysis = analysis.strip() or "No AI insight returned."
        except Exception as e:
            logger.warning("AI generation failed: %s", e)
            analysis = "Quick analysis: portfolio enumerated; detailed AI insights unavailable right now."

        await response_handler.emit_json("FULL_ANALYSIS", {
            "wallet": wallet,
            "estimated_value_usd": total_value_usd,
            "analysis": analysis,
            "count": len(all_holdings),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "provider": getattr(self.model_provider, "provider", "fallback"),
            "model": getattr(self.model_provider, "model", "n/a")
        })

        await response_handler.emit_text_block("DONE", f"Completed analysis for {wallet}")
        await response_handler.complete()