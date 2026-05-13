"""Ingest faqs.pdf into the faq_chunks table. Safe to run multiple times."""

import asyncio

from travel_assistant.rag.ingest import run_ingest


async def main() -> None:
    print("loading model and embedding chunks...")
    n = await run_ingest()
    print(f"done: {n} chunks ingested")


if __name__ == "__main__":
    asyncio.run(main())
