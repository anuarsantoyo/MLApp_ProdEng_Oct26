# Modules, packages and routers

One idea, in three steps: **importing means "run that file once, then give me a name for what is inside it"**.
A FastAPI router is that same idea applied to routes.

Run every command below with the venv active (`source .venv/bin/activate` from the repo root).

## Part 1: a module is a file

```bash
cd MLAppDev/ModB/Sprint1/router_class/flat
python main.py
```

`helpers.py` printed once even though `main.py` imported it twice. Also notice the `__name__` value
in each line: `"helpers"` when the file is imported, `"__main__"` when you run the file yourself.
That is the whole reason for `if __name__ == "__main__":`.

Then the failure that makes the next step necessary. From `router_class/`:

```bash
cd ..
python -c "from helpers import greet"
```

`ModuleNotFoundError`. The import system searches a fixed list of folders (`sys.path`), it does not
search your whole disk. The folder of the script you run is the first one in that list.

## Part 2: a package is a folder with a front door

```bash
cd package
python main.py
```

Same function as `../flat/helpers.py`, only its address changed. Three things to look at:

- `shop/__init__.py` runs when the package is imported. The print proves it.
- `from shop import greet` works only because `__init__.py` exported it. Without `__init__.py`,
  `main.py` would have to say `from shop.helpers import greet`.
- The dot in `from .helpers import greet` means "inside this package". Without the dot, Python
  searches `sys.path` and fails.

## Part 3: routers are that same idea

The "before". Every route in one file, `/items` written three times:

```bash
cd ../routers
uvicorn app_v1:app --reload --port 8011
```

In a second terminal:

```bash
cd MLAppDev/ModB/Sprint1/router_class/routers
python client.py
```

Stop the server. Now the "after". The routes live in `routers/`, and `main.py` only plugs them in:

```bash
uvicorn main:app --reload --port 8011
```

```bash
python client.py
```

Run the server from inside this folder, because `main.py` says `from routers import ...` and
`routers/` is a folder next to it, not next to wherever you started the terminal. From the repo
root the same server needs the folder on `sys.path`, which is what `--app-dir` does:

```bash
uvicorn main:app --app-dir MLAppDev/ModB/Sprint1/router_class/routers --port 8011
```

Without `--app-dir` you get `ModuleNotFoundError: No module named 'routers'`, which is exactly the
failure from part 1.

The five lines come out identical, and `http://127.0.0.1:8011/docs` now has two sections, `items`
and `health`, because of `tags`.

What to look at:

- `routers/items.py` defines `router = APIRouter()`. Every decorator you know works on it unchanged.
  An `APIRouter` is a smaller `FastAPI`.
- A router cannot be started with `uvicorn`. It is a drawer of routes; `include_router` plugs it in.
- `from routers import items` gives you the file, exactly like `from shop import greet` gave you the
  function in part 1. Then `items.router` is the object defined inside `routers/items.py`.
- There is no `/items` anywhere inside `routers/items.py`. That prefix is added once, in `main.py`:
  `app.include_router(items.router, prefix="/items")`.
- A prefix has two homes. `items` gets it in `main.py` (`prefix="/items"`), and `health` gets it in
  its own file (`APIRouter(prefix="/health")`), so `main.py` plugs that one in with nothing else.
  Same URLs either way. The file that owns the prefix is the only one you edit when the URL changes.

Moving all item routes to `/v2/items` is now one word in `main.py`, not four edits spread over
decorators.

## Files

| File | What it shows |
|---|---|
| `flat/helpers.py`, `flat/main.py` | a definition in another file, imported by name |
| `package/shop/__init__.py` | the front door: what `from shop import ...` can see |
| `routers/app_v1.py` | the "before": all routes in one file |
| `routers/routers/items.py` | `APIRouter`, no prefix in the file, same decorators |
| `routers/routers/health.py` | a router that carries its own `prefix` and `tags` |
| `routers/routers/__init__.py` | empty file that makes the folder a package |
| `routers/main.py` | `include_router`, with the prefix here or in the router file |
| `routers/client.py` | same five requests against both versions |
