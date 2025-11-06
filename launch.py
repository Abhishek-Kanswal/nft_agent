#!/usr/bin/env python3
"""
Launcher script that patches typing.Self before importing anything
"""
import sys
import os

# MUST BE FIRST - Patch typing before any imports
if sys.version_info < (3, 11):
    import typing
    try:
        from typing_extensions import Self
    except ImportError:
        # Create a fake Self if typing_extensions is not available
        class Self:
            pass
    typing.Self = Self
    sys.modules['typing'].Self = Self

# Now import the framework and your app
try:
    from src.nft_agent import NFTPortfolioAgent
    import asyncio
    
    async def main():
        agent = NFTPortfolioAgent()
        print("✅ NFT Agent started successfully!")
        # Add your main application logic here
        
    if __name__ == "__main__":
        asyncio.run(main())
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
