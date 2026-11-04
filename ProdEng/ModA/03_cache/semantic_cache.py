# uvicorn ProdEng.03_cache.semantic_cache:app --reload --port 8002
# (run from the repo root, or run `uvicorn semantic_cache:app --reload --port 8002` inside this folder)

import hashlib
import json
import os
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel

# The .env lives at the repo root, the policy file next to this script
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(__file__).with_name("heliodesk-policies.md")

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to the .env file at the repo root.")
if not POLICY_PATH.exists():
    raise RuntimeError(f"Policy file not found: {POLICY_PATH}")

# Same OpenRouter embedding model as sprint_2
embeddings = OpenAIEmbeddings(
    model="google/gemini-embedding-001",
    base_url=BASE_URL,
    api_key=API_KEY,
    check_embedding_ctx_length=False,  # send plain text, not OpenAI token ids
)

# 1. Split the handbook into chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=850, chunk_overlap=120)
text = POLICY_PATH.read_text(encoding="utf-8")
chunks = [
    Document(page_content=piece, metadata={"chunk": i})
    for i, piece in enumerate(splitter.split_text(text))
]

# 2. One Chroma client, two collections: the handbook and the semantic cache
chroma_client = chromadb.EphemeralClient()

vectorstore = Chroma(
    client=chroma_client,
    collection_name="heliodesk",
    embedding_function=embeddings,
    collection_metadata={"hnsw:space": "cosine"},
)
vectorstore.add_documents(chunks, ids=[str(c.metadata["chunk"]) for c in chunks])

cache_collection = chroma_client.get_or_create_collection(
    name="semantic_cache",
    embedding_function=None,  # we pass the vectors ourselves
    metadata={"hnsw:space": "cosine"},
)

# question -> embed -> nearest chunks
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 3. Chat model through OpenRouter
llm = ChatOpenAI(
    model="google/gemini-2.5-flash-lite",
    base_url=BASE_URL,
    api_key=API_KEY,
    temperature=0,
)

answer_chain = (
    ChatPromptTemplate.from_template(
        "Answer the question using only the policy context."
        "If the context is not enough, say what is missing.\n\n"
        "Context:\n{context}\n\nQuestion: {question}"
    )
    | llm
    | StrOutputParser()
)

app = FastAPI(title="HelioDesk policy chatbot (semantic cache)")

# A cached question is a hit when its cosine similarity is at least this value.
# Raise it for fewer (safer) hits, lower it for more hits.
SIMILARITY_THRESHOLD = 0.9


def normalize(question: str) -> str:
    # lowercase + trim + collapse whitespace
    return " ".join(question.lower().split())


def cache_lookup(vector, threshold=SIMILARITY_THRESHOLD):
    results = cache_collection.query(
        query_embeddings=[vector],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )
    if not results["ids"][0]:
        return None

    # Chroma cosine space returns distance = 1 - cosine similarity
    similarity = 1 - results["distances"][0][0]
    if similarity < threshold:
        return None

    metadata = results["metadatas"][0][0]
    return {
        "question": results["documents"][0][0],
        "answer": metadata["answer"],
        "sources": json.loads(metadata["sources"]),
        "similarity": similarity,
    }


def cache_store(normalized_question, vector, answer, sources):
    # Chroma metadata only takes simple values, so sources become a JSON string
    cache_collection.upsert(
        ids=[hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()],
        embeddings=[vector],
        documents=[normalized_question],
        metadatas=[{"answer": answer, "sources": json.dumps(sources)}],
    )


class ChatRequest(BaseModel):
    question: str


# Example request:
# curl http://127.0.0.1:8002/cache
@app.get("/cache")
def read_cache():
    entries = cache_collection.get(include=["documents", "metadatas"])
    return [
        {
            "question": document,
            "answer": metadata["answer"],
            "sources": json.loads(metadata["sources"]),
        }
        for document, metadata in zip(entries["documents"], entries["metadatas"])
    ]


# Example request:
# curl -X POST http://127.0.0.1:8002/chat -H "Content-Type: application/json" -d '{"question": "How long do export files stay available?"}'
@app.post("/chat")
def chat(request: ChatRequest):
    start = time.perf_counter()
    normalized = normalize(request.question)
    vector = embeddings.embed_query(normalized)  # one embedding call per request

    hit = cache_lookup(vector)
    if hit:
        return {
            "answer": hit["answer"],
            "sources": hit["sources"],
            "cached": True,
            "matched_question": hit["question"],
            "similarity": round(hit["similarity"], 4),
            "latency_seconds": round(time.perf_counter() - start, 4),
        }

    docs = retriever.invoke(request.question)
    context = "\n\n".join(f"[chunk {d.metadata['chunk']}] {d.page_content}" for d in docs)
    
    answer = answer_chain.invoke({"context": context, "question": request.question})
    sources = [d.metadata["chunk"] for d in docs]

    cache_store(normalized, vector, answer, sources)

    return {
        "answer": answer,
        "sources": sources,
        "cached": False,
        "matched_question": None,
        "similarity": None,
        "latency_seconds": round(time.perf_counter() - start, 2),
    }
