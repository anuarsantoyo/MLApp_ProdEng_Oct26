# python ProdEng/05_user_rag/seed.py
# (run from the repo root, or run `python seed.py` inside this folder)

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# The .env lives at the repo root, the policy file and the data next to this script
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(__file__).with_name("heliodesk-policies.md")
DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "app.db"
CHROMA_DIR = DATA_DIR / "chroma"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    user_name TEXT NOT NULL,
    country TEXT NOT NULL,
    role TEXT NOT NULL
);
"""

# Fake customers used by the example
USERS = [
    (1, "Ana Torres", "Mexico", "owner"),
    (2, "Luis Mendez", "Spain", "billing_manager"),
    (3, "Priya Nair", "India", "agent"),
    (4, "Emma Chen", "Singapore", "admin"),
    (5, "Diego Ruiz", "Germany", "contractor"),
]


def create_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO users (user_id, user_name, country, role) VALUES (?, ?, ?, ?)",
            USERS,
        )
        conn.commit()
    finally:
        conn.close()


load_dotenv(ROOT / ".env")
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to the .env file at the repo root.")
if not POLICY_PATH.exists():
    raise RuntimeError(f"Policy file not found: {POLICY_PATH}")

# Same embedding model as seed and serve, otherwise query vectors live in a
# different space than the stored chunks.
embeddings = OpenAIEmbeddings(
    model="google/gemini-embedding-001",
    base_url=BASE_URL,
    api_key=API_KEY,
    check_embedding_ctx_length=False,  # send plain text, not OpenAI token ids
)

# 1. User database (fake databank)
create_db()
print(f"User database ready at {DB_PATH} ({len(USERS)} users)")

# 2. Persistent vector store
vectorstore = Chroma(
    persist_directory=str(CHROMA_DIR),
    collection_name="heliodesk",
    embedding_function=embeddings,
    collection_metadata={"hnsw:space": "cosine"},
)

if vectorstore.get(limit=1)["ids"]:
    # Second run: the vectors are already on disk, so no embedding calls
    print(f"Policy already indexed in {CHROMA_DIR} (skipping embeddings)")
else:
    splitter = RecursiveCharacterTextSplitter(chunk_size=850, chunk_overlap=120)
    text = POLICY_PATH.read_text(encoding="utf-8")
    chunks = [
        Document(page_content=piece, metadata={"chunk": i})
        for i, piece in enumerate(splitter.split_text(text))
    ]
    vectorstore.add_documents(chunks, ids=[str(c.metadata["chunk"]) for c in chunks])
    print(f"Indexed {len(chunks)} policy chunks into {CHROMA_DIR}")
