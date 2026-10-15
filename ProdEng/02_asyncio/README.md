# asyncio and FastAPI examples

## Setup
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 1. The notebook: `asyncio_notebook.ipynb`
Open it in VS Code (or Jupyter) and run the cells from top to bottom.
Parts: 1 timing sync functions · 2 async/await · 3 `gather` and `asyncio.run` · 4 `Semaphore` · 5 `create_task`.
It creates two small files next to it (`demo.py`, `cutoff.py`) when you run it.

## 2. FastAPI: `fastapi/`
Use two terminals, both inside the `fastapi` folder. All apps use port 8000, so run one at a time (Ctrl+C to stop).

**Blocking vs async**
```bash
uvicorn sync_app:app --port 8000        # terminal 1
python send_requests.py                 # terminal 2   -> 1.6, 3.1, 4.6, 6.1, 7.6 s
```
```bash
uvicorn async_app:app --port 8000       # terminal 1
python send_requests.py                 # terminal 2   -> all five at about 1.6 s
```

**Background task**
```bash
uvicorn background_app:app --port 8000          # terminal 1
python send_background_requests.py              # terminal 2   -> 202 at 0.2 s, "processing", then "finished"
```
Or by hand:
```bash
curl -X POST localhost:8000/answer/async        # {"job_id":1}   (HTTP 202)
curl localhost:8000/answer/1                    # right away: processing, 2 s later: finished
```

| File | What it shows |
|---|---|
| `sync_app.py` | five blocking functions behind `POST /answer` |
| `async_app.py` | the same, with `async def`, `await` and `asyncio.sleep` |
| `send_requests.py` | sends five requests at once with `gather` |
| `background_app.py` | `POST /answer/async` returns 202 + job id; the work finishes in the background |
| `send_background_requests.py` | sends five requests, checks each job right away and 2 s later |
