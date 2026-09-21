"""
Vector DB Seeding Script
========================
Reads server/data/educational_content.json, generates 1536-dim embeddings via
Gemini Embedding 2 (gemini-embedding-2-preview) using the official google-genai SDK,
and upserts vectors + metadata into Pinecone.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone

# Load environment variables
for env_path in [Path("server/.env"), Path(".env"), Path(__file__).parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break


def seed_pinecone():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pinecone_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "pathforge-educational-content")

    if not gemini_key or not pinecone_key:
        raise ValueError("GEMINI_API_KEY and PINECONE_API_KEY environment variables must be set.")

    print(f"Connecting to Pinecone index '{index_name}'...")
    client = genai.Client(api_key=gemini_key)
    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index(index_name)

    # Locate educational_content.json
    candidates = [
        Path("server/data/educational_content.json"),
        Path("data/educational_content.json"),
        Path(__file__).parent.parent / "data" / "educational_content.json",
    ]
    data_path = None
    for candidate in candidates:
        if candidate.exists():
            data_path = candidate.resolve()
            break

    if not data_path:
        raise FileNotFoundError("Could not find 'server/data/educational_content.json'.")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])
    print(f"Generating 1536-dim embeddings with 'gemini-embedding-2-preview' for {len(resources)} items...")

    vectors_to_upsert = []
    for idx, item in enumerate(resources, 1):
        text_payload = f"{item['title']}. {' '.join(item.get('tags', []))}. {item['content_snippet']}"
        print(f"[{idx}/{len(resources)}] Embedding: {item['title'][:45]}...")

        # Generate 1536-dim vector using Gemini Embedding 2
        resp = client.models.embed_content(
            model="gemini-embedding-2-preview",
            contents=text_payload,
            config=types.EmbedContentConfig(output_dimensionality=1536)
        )
        vector_values = resp.embeddings[0].values

        vectors_to_upsert.append({
            "id": item["id"],
            "values": vector_values,
            "metadata": {
                "concept_id": item["concept_id"],
                "title": item["title"],
                "resource_type": item["resource_type"],
                "url_or_ref": item.get("url_or_ref", ""),
                "content_snippet": item["content_snippet"],
                "estimated_minutes": item.get("estimated_minutes", 15),
                "difficulty": item.get("difficulty", "intermediate"),
                "tags": item.get("tags", [])
            }
        })

    print(f"Upserting {len(vectors_to_upsert)} vectors into Pinecone...")
    index.upsert(vectors=vectors_to_upsert)
    print(f"Successfully seeded Pinecone index '{index_name}' with gemini-embedding-2-preview!")


if __name__ == "__main__":
    seed_pinecone()
