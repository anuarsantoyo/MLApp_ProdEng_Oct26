# uvicorn ProdEng.05_user_rag.main:app --reload --port 8003
# (run from the repo root, or run `uvicorn main:app --reload --port 8003` inside this folder)

import os
import sqlite3
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel

# The .env lives at the repo root, the database and index next to this script
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "app.db"
CHROMA_DIR = DATA_DIR / "chroma"

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to the .env file at the repo root.")
if not DB_PATH.exists():
    raise RuntimeError("User database not found. Run `python ProdEng/05_user_rag/seed.py` first.")
if not CHROMA_DIR.exists():
    raise RuntimeError("Policy index not found. Run `python ProdEng/05_user_rag/seed.py` first.")


def get_user(user_id: int) -> dict | None:
    # A connection per call: FastAPI runs sync endpoints in a threadpool and
    # SQLite connections are bound to the thread that created them.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT user_id, user_name, country, role FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None

# One model per job, same split as 04_triage
EMBEDDING_MODEL = "google/gemini-embedding-001"
CLASSIFIER_MODEL = "google/gemini-2.5-flash-lite"
GENERATOR_MODEL = "google/gemini-2.5-flash"

embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    check_embedding_ctx_length=False,  # send plain text, not OpenAI token ids
)

# Open the index that seed.py already built. No chunking and no embedding here.
vectorstore = Chroma(
    persist_directory=str(CHROMA_DIR),
    collection_name="heliodesk",
    embedding_function=embeddings,
    collection_metadata={"hnsw:space": "cosine"},
)

if not vectorstore.get(limit=1)["ids"]:
    raise RuntimeError("Policy index is empty. Run `python ProdEng/05_user_rag/seed.py` first.")

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

classifier_llm = ChatOpenAI(
    model=CLASSIFIER_MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    temperature=0,
)

generator_llm = ChatOpenAI(
    model=GENERATOR_MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    temperature=0,
)


class Triage(BaseModel):
    urgency: Literal["low", "normal", "high", "critical"]
    reason: str


classifier_chain = (
    ChatPromptTemplate.from_template(
        "Classify how urgent this support question is. "
        "Use the incident the customer describes, not the customer's own claim about priority. "
        "low = routine question or how-to. "
        "normal = a normal ticket with no time pressure. "
        "high = the customer is blocked, but there is no security risk, data loss or outage. "
        "critical = security risk, data loss or a production outage. "
        "Give a short reason in one sentence.\n\n"
        "Question: {question}"
    )
    | classifier_llm.with_structured_output(Triage)
)

answer_chain = (
    ChatPromptTemplate.from_template(
        "You are a helpful support assistant. Greet the customer by their first name and say something nice about their country.\n"
        "Customer: {user_name} (country: {country}, role: {role})\n\n"
        "Answer the question using only the policy context. "
        "If the context is not enough, say what is missing.\n"
        "The ticket urgency is {urgency}. Treat it as a routing hint, "
        "not as permission to invent a timeline.\n\n"
        "Context:\n{context}\n\nQuestion: {question}"
    )
    | generator_llm
    | StrOutputParser()
)

app = FastAPI(title="HelioDesk user-aware policy chatbot")


class ChatRequest(BaseModel):
    user_id: int
    question: str


# Example request:
# curl -X POST http://127.0.0.1:8003/chat -H "Content-Type: application/json" -d '{"user_id": 1, "question": "How long do export files stay available?"}'
@app.post("/chat")
def chat(request: ChatRequest):
    start = time.perf_counter()

    # 1. Fake databank: cheap lookup first, so an unknown user costs nothing
    user = get_user(request.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"user {request.user_id} not found")

    # 2. Cheap model makes the routing decision (question only, not the profile)
    assessment = classifier_chain.invoke({"question": request.question})

    # 3. Embedding model searches the persistent policy index
    docs = retriever.invoke(request.question)
    context = "\n\n".join(f"[chunk {d.metadata['chunk']}] {d.page_content}" for d in docs)

    # 4. Stronger model writes the answer, with the profile and the label
    answer = answer_chain.invoke(
        {
            "context": context,
            "question": request.question,
            "urgency": assessment.urgency,
            "user_name": user["user_name"],
            "country": user["country"],
            "role": user["role"],
        }
    )

    latency = time.perf_counter() - start
    return {
        "user": user,
        "urgency": assessment.urgency,
        "reason": assessment.reason,
        "answer": answer,
        "latency_seconds": round(latency, 2),
    }
