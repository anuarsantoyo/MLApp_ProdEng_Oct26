# uvicorn ProdEng.04_triage.main:app --reload --port 8002
# (run from the repo root, or run `uvicorn main:app --reload --port 8002` inside this folder)

import os
import time
from pathlib import Path
from typing import Literal

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

# One model per job. Pay for what each step actually needs.
# Prices per 1M tokens on OpenRouter (prompt / completion):
#   gemini-embedding-001    -> vectors only, no chat completion
#   gemini-2.5-flash-lite   -> $0.10 / $0.40   small model, short label output
#   gemini-2.5-flash        -> $0.30 / $2.50   stronger model, writes the answer
EMBEDDING_MODEL = "google/gemini-embedding-001"
CLASSIFIER_MODEL = "google/gemini-2.5-flash-lite"
GENERATOR_MODEL = "google/gemini-2.5-flash"

# 1. Embedding model: question and chunks -> vectors
embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    check_embedding_ctx_length=False,  # send plain text, not OpenAI token ids
)

# 2. Split the handbook into chunks and store them in ChromaDB (in memory)
splitter = RecursiveCharacterTextSplitter(chunk_size=850, chunk_overlap=120)
text = POLICY_PATH.read_text(encoding="utf-8")
chunks = [
    Document(page_content=piece, metadata={"chunk": i})
    for i, piece in enumerate(splitter.split_text(text))
]

vectorstore = Chroma(
    client=chromadb.EphemeralClient(),
    collection_name="heliodesk",
    embedding_function=embeddings,
    collection_metadata={"hnsw:space": "cosine"},
)
vectorstore.add_documents(chunks, ids=[str(c.metadata["chunk"]) for c in chunks])

# question -> embed -> nearest chunks
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 3. Classification model: question -> urgency label (cheap and short)
classifier_llm = ChatOpenAI(
    model=CLASSIFIER_MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    temperature=0,
)

# 4. Generation model: context + question + label -> answer (the expensive part)
generator_llm = ChatOpenAI(
    model=GENERATOR_MODEL,
    base_url=BASE_URL,
    api_key=API_KEY,
    temperature=1,
)


class Triage(BaseModel):
    urgency: Literal["low", "normal", "high", "critical"]
    reason: str


classifier_chain = (
    ChatPromptTemplate.from_template(
        "Classify the support question’s urgency based on the incident described, not the customer’s claimed priority. " \
        "Use: low = routine/how-to; normal = no time pressure; high = blocked but no security risk, data loss, or outage; " \
        "critical = security risk, data loss, or production outage. Give a one-sentence reason.\n\n Question: {question}"
    )
    | classifier_llm.with_structured_output(Triage)
)

answer_chain = (
    ChatPromptTemplate.from_template(
        "Answer the question using only the policy context. "
        "If the context is not enough, say what is missing.\n"
        "The ticket urgency is {urgency}. Treat it as a routing hint, "
        "not as permission to invent a timeline.\n\n"
        "Context:\n{context}\n\nQuestion: {question}"
    )
    | generator_llm
    | StrOutputParser()
)

app = FastAPI(title="HelioDesk triage chatbot")


class TriageRequest(BaseModel):
    question: str


# Example request:
# curl -X POST http://127.0.0.1:8002/triage -H "Content-Type: application/json" -d '{"question": "Our production workspace is down and we cannot log in."}'
@app.post("/triage")
def triage(request: TriageRequest):
    start = time.perf_counter()

    # 1. Cheap model makes the routing decision
    assessment = classifier_chain.invoke({"question": request.question})

    # 2. Embedding model finds the policy evidence
    docs = retriever.invoke(request.question)
    context = "\n\n".join(f"[chunk {d.metadata['chunk']}] {d.page_content}" for d in docs)

    # 3. Stronger model writes the answer, knowing the label
    answer = answer_chain.invoke(
        {"context": context, "question": request.question, "urgency": assessment.urgency}
    )

    latency = time.perf_counter() - start
    return {
        "urgency": assessment.urgency,
        "reason": assessment.reason,
        "answer": answer,
        "sources": [d.metadata["chunk"] for d in docs],
        "latency_seconds": round(latency, 2),
    }
