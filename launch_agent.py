#!/usr/bin/env python3
import sys
if sys.version_info < (3, 11):
    from typing_extensions import Self
    import typing
    typing.Self = Self

from src.nft_agent import NFTPortfolioAgent
import asyncio

async def main():
    agent = NFTPortfolioAgent()
    print("NFT Agent started successfully!")
    # Add your main logic here

if __name__ == "__main__":
    asyncio.run(main())
