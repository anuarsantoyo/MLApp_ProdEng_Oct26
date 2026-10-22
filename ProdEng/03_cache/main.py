# uvicorn ProdEng.03_cache.main:app --reload --port 8000
# (run from the repo root, or run `uvicorn main:app --reload --port 8000` inside this folder)

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

# 2. Embed the chunks and store them in ChromaDB (in memory)
vectorstore = Chroma(
    client=chromadb.EphemeralClient(),
    collection_name="heliodesk",
    embedding_function=embeddings,
    collection_metadata={"hnsw:space": "cosine"},
)
vectorstore.add_documents(chunks, ids=[str(c.metadata["chunk"]) for c in chunks])

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

app = FastAPI(title="HelioDesk policy chatbot")


class ChatRequest(BaseModel):
    question: str


# Example request:
# curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"question": "Can an external auditor get a workspace export, and how is it delivered?"}'
@app.post("/chat")
def chat(request: ChatRequest):
    start = time.perf_counter()

    docs = retriever.invoke(request.question)
    context = "\n\n".join(f"[chunk {d.metadata['chunk']}] {d.page_content}" for d in docs)
    answer = answer_chain.invoke({"context": context, "question": request.question})

    latency = time.perf_counter() - start
    return {
        "latency_seconds": round(latency, 2),
        "answer": answer
    }
