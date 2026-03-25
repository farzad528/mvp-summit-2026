"""
Setup script: Creates Azure AI Search indexes and pushes documents with embeddings.
Creates two indexes:
  - mvp-summit-kb: sessions + campus guide data
  - contoso-policy-kb: Contoso insurance policy chunks

Usage:
  cp code/.env.sample code/.env   # fill in your endpoints
  python scripts/setup_indexes.py
"""

import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "code", ".env"))

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ExhaustiveKnnAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from openai import AzureOpenAI

# ── Configuration ────────────────────────────────────────────────────────────

SEARCH_ENDPOINT = os.environ["AZURE_AI_SEARCH_ENDPOINT"]
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
EMBEDDING_MODEL = os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
EMBEDDING_DIMS = 3072
SEARCH_ADMIN_KEY = os.getenv("AZURE_AI_SEARCH_KEY", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ── Helpers ──────────────────────────────────────────────────────────────────

aad_credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    aad_credential, "https://cognitiveservices.azure.com/.default"
)
openai_client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT,
    azure_ad_token_provider=token_provider,
    api_version="2024-10-21",
)

# Use admin key for search data plane (RBAC may not be configured)
if SEARCH_ADMIN_KEY:
    search_credential = AzureKeyCredential(SEARCH_ADMIN_KEY)
else:
    search_credential = aad_credential
index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=search_credential)


def embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    result = openai_client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    return [item.embedding for item in result.data]


def create_kb_index(index_name: str):
    """Create a search index with text + vector fields + semantic config."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(
            name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"
        ),
        SimpleField(
            name="category", type=SearchFieldDataType.String, filterable=True, facetable=True
        ),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMS,
            vector_search_profile_name="myHnswProfile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="myHnsw"),
            ExhaustiveKnnAlgorithmConfiguration(name="myExhaustiveKnn"),
        ],
        profiles=[
            VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw"),
        ],
    )

    semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="category")],
        ),
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    print(f"  Creating index '{index_name}'...")
    index_client.create_or_update_index(index)
    print(f"  ✓ Index '{index_name}' ready")


# ── Build MVP Summit KB documents ────────────────────────────────────────────


def build_summit_documents() -> list[dict]:
    """Build documents from sessions.json and campus-guide.json."""
    docs = []

    # Sessions
    with open(os.path.join(DATA_DIR, "sessions.json"), encoding="utf-8") as f:
        sessions_data = json.load(f)

    for s in sessions_data["sessions"]:
        content = (
            f"Session: {s['title']}\n"
            f"Track: {s['track']}\n"
            f"Speaker: {s['speaker']}\n"
            f"Date: {s['date']}, Time: {s['time']}\n"
            f"Location: {s['building']}, Room: {s['room']}\n"
            f"Level: {s.get('level', 'N/A')}\n"
            f"Description: {s['description']}"
        )
        docs.append(
            {
                "id": s["id"],
                "title": s["title"],
                "content": content,
                "category": s["track"],
                "source": "sessions.json",
            }
        )

    # Campus guide — buildings
    with open(os.path.join(DATA_DIR, "campus-guide.json"), encoding="utf-8") as f:
        campus = json.load(f)

    for b in campus["buildings"]:
        content = (
            f"Building: {b['name']}\n"
            f"Tracks: {', '.join(b['tracks'])}\n"
            f"Rooms: {', '.join(b['rooms'])}\n"
            f"Notes: {b['notes']}\n"
            f"Cafeteria: {b['cafeteria']}\n"
            f"Parking: {b['parking']}"
        )
        docs.append(
            {
                "id": f"campus-{b['name'].replace(' ', '-').lower()}",
                "title": b["name"],
                "content": content,
                "category": "Campus",
                "source": "campus-guide.json",
            }
        )

    # Shuttle info
    shuttle = campus["shuttle"]
    docs.append(
        {
            "id": "campus-shuttle",
            "title": "Connector Shuttle",
            "content": (
                f"Shuttle: {shuttle['name']}\n"
                f"Frequency: {shuttle['frequency']}\n"
                f"Hours: {shuttle['hours']}\n"
                f"Stops: {', '.join(shuttle['stops'])}\n"
                f"Note: {shuttle['note']}"
            ),
            "category": "Campus",
            "source": "campus-guide.json",
        }
    )

    # Meals
    meals = campus["meals"]
    docs.append(
        {
            "id": "campus-meals",
            "title": "Dining and Meals",
            "content": (
                f"Breakfast: {meals['breakfast']}\n"
                f"Lunch: {meals['lunch']}\n"
                f"Dinner: {meals['dinner']}\n"
                f"Tip: {meals['tip']}"
            ),
            "category": "Campus",
            "source": "campus-guide.json",
        }
    )

    # WiFi + Emergency
    docs.append(
        {
            "id": "campus-wifi",
            "title": "WiFi and Emergency Info",
            "content": (
                f"WiFi Network: {campus['wifi']['network']}\n"
                f"WiFi Password: {campus['wifi']['password']}\n"
                f"Security Phone: {campus['emergency']['security']}\n"
                f"Medical: {campus['emergency']['medical']}"
            ),
            "category": "Campus",
            "source": "campus-guide.json",
        }
    )

    return docs


# ── Build Contoso Policy KB documents ────────────────────────────────────────


def build_policy_documents() -> list[dict]:
    """Chunk contoso-returns-policy.md by section headings."""
    with open(
        os.path.join(DATA_DIR, "contoso-returns-policy.md"), encoding="utf-8"
    ) as f:
        content = f.read()

    # Split by ## headings
    sections = re.split(r"\n(?=## )", content)
    docs = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # Extract first heading as title
        lines = section.split("\n")
        title_line = lines[0].lstrip("#").strip()
        if not title_line:
            title_line = f"Contoso Policy Section {i}"

        doc_id = f"policy-{i:03d}-{re.sub(r'[^a-z0-9]', '-', title_line.lower())[:40]}"

        docs.append(
            {
                "id": doc_id,
                "title": title_line,
                "content": section,
                "category": "Policy",
                "source": "contoso-returns-policy.md",
            }
        )

    return docs


# ── Push documents with embeddings ───────────────────────────────────────────


def push_documents(index_name: str, docs: list[dict]):
    """Generate embeddings and upload documents to the search index."""
    print(f"  Generating embeddings for {len(docs)} documents...")

    # Batch embeddings (max ~16 at a time for rate limits)
    batch_size = 16
    all_embeddings = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        texts = [d["content"] for d in batch]
        embeddings = embed(texts)
        all_embeddings.extend(embeddings)
        if i + batch_size < len(docs):
            time.sleep(0.5)  # rate limit buffer

    for doc, emb in zip(docs, all_embeddings):
        doc["content_vector"] = emb

    print(f"  Uploading {len(docs)} documents to '{index_name}'...")
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT, index_name=index_name, credential=search_credential
    )
    result = search_client.upload_documents(docs)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"  ✓ {succeeded}/{len(docs)} documents uploaded successfully")


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    print("\n═══ Foundry IQ Demo — Index Setup ═══\n")

    # 1. MVP Summit KB
    print("1. MVP Summit KB (mvp-summit-kb)")
    create_kb_index("mvp-summit-kb")
    summit_docs = build_summit_documents()
    push_documents("mvp-summit-kb", summit_docs)

    # 2. Contoso Policy KB
    print("\n2. Contoso Policy KB (contoso-policy-kb)")
    create_kb_index("contoso-policy-kb")
    policy_docs = build_policy_documents()
    push_documents("contoso-policy-kb", policy_docs)

    print("\n═══ Setup Complete ═══")
    print(f"  MVP Summit KB: {len(summit_docs)} documents")
    print(f"  Contoso Policy KB: {len(policy_docs)} documents")
    print("  Both indexes are ready for agent grounding.\n")


if __name__ == "__main__":
    main()
