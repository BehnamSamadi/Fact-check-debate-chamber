"""
Initialize a Langfuse project and output API keys for .env.

Usage:
    python scripts/setup_langfuse.py

Requires Langfuse to be running. Set LANGFUSE_URL if not default.
"""
import os
import sys

import httpx

LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://localhost:3100")


def main():
    print(f"Langfuse URL: {LANGFUSE_URL}")
    print()
    print("Steps to connect Langfuse:")
    print()
    print(f"  1. Open {LANGFUSE_URL} in your browser")
    print("  2. Create an account (first time only)")
    print("  3. Go to Settings > Projects and click 'New Project'")
    print("  4. Name it 'Debate Chamber' and click Create")
    print("  5. Click the new project > API Keys")
    print("  6. Copy the Public Key and Secret Key")
    print()
    print("  Then add these lines to your .env file:")
    print()
    print("  LANGFUSE_PUBLIC_KEY=pk-lf-...")
    print("  LANGFUSE_SECRET_KEY=sk-lf-...")
    print()
    print("  And restart the agents:")
    print("  docker compose restart orchestrator skeptic-agent researcher-agent analyst-agent")
    print()


if __name__ == "__main__":
    main()
