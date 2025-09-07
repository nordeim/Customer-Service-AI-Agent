Got it — let’s make this a **developer‑friendly, hot‑reload‑enabled workflow** so you can run your full stack, edit code locally, and see changes instantly without rebuilding the image every time.  

I’ll break this into **three parts**:  
1. **Accessing and using the running API**  
2. **Enabling hot‑reload in your container**  
3. **Running the stack in “live development” mode**  

---

## **1. Accessing and using the running API**

Once you run:

```bash
docker compose up --build
```

and all services are healthy:

- **From your host machine**  
  - Base URL: `http://localhost:8000` (or whatever `${API_PORT}` is set to in `.env`)  
  - Interactive docs:  
    - Swagger UI → `http://localhost:8000/docs`  
    - ReDoc → `http://localhost:8000/redoc`  
  - Health check:  
    ```bash
    curl http://localhost:8000/health
    ```

- **From another container in the same network**  
  - Use the service name `api` and port `8000`:  
    ```
    http://api:8000
    ```

- **Exec into the API container**  
  ```bash
  docker compose exec api sh
  ```
  (or `/bin/bash` if installed)

---

## **2. Enabling hot‑reload in the API container**

Right now, your `Dockerfile` runs:

```dockerfile
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

That’s production‑style — no reload. For development, you want:

```dockerfile
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src"]
```

**Why this works:**
- `--reload` tells Uvicorn to watch for file changes and restart automatically.
- `--reload-dir /app/src` limits watching to your source directory (avoids unnecessary reloads).

---

## **3. Running the stack in “live development” mode**

You already have **bind mounts** in `docker-compose.yml`:

```yml
volumes:
  - ./src:/app/src
  - ./tests:/app/tests
  - ./logs:/app/logs
```

This means:
- Any change you make in `./src` or `./tests` on your host is instantly visible inside the container.
- With `--reload` enabled, Uvicorn will restart the app automatically.

---

### **Step‑by‑step setup for hot‑reload**

**Option A — Temporary dev override (no permanent file changes)**  
Create a `docker-compose.override.yml` (Compose automatically merges it):

```yml
services:
  api:
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src
    environment:
      - ENVIRONMENT=development
```

Then run:
```bash
docker compose up --build
```

**Option B — Bake into Dockerfile for dev builds**
- Change the `CMD` in your `Dockerfile` to include `--reload` (as above).
- Or use a build arg to switch between prod/dev commands.

---

### **Workflow tips for smooth dev experience**

1. **Start the stack**
   ```bash
   docker compose up --build
   ```
   Wait until `api` logs show:
   ```
   Uvicorn running on http://0.0.0.0:8000 (Reloading)
   ```

2. **Edit code locally**
   - Save changes in `./src` → container sees them instantly → Uvicorn reloads.

3. **Run tests inside container**
   ```bash
   docker compose exec api pytest
   ```

4. **Debugging**
   - Add `--log-level debug` to the uvicorn command for verbose logs.
   - Use `docker compose logs -f api` to tail logs live.

5. **Stop stack**
   ```bash
   docker compose down
   ```
   Add `-v` if you want to remove volumes (wipes DBs).

---

### **Extra: Speeding up reloads**
- Install `watchfiles` in your requirements for faster reload detection:
  ```bash
  pip install watchfiles
  ```
  Then Uvicorn will automatically use it for file watching.

---

✅ **Bottom line:**  
With your current bind mounts + `--reload`, you can treat the container like a local Python environment — edit, save, refresh your browser, and see changes instantly. No rebuilds, no restarts.

---

If you want, I can prepare a **dual‑mode setup** so you can run the same stack in **production mode** or **hot‑reload dev mode** just by switching a single environment variable. That way you don’t have to edit Dockerfiles or Compose files each time. Would you like me to design that?

---
Yes — in your setup, the **Python application is deployed inside the `api` service container**.  
That container is built from your `Dockerfile` and runs your FastAPI app with Uvicorn as the ASGI server.

Here’s how it works and how you can reach it:

---

## **Where the app lives**
- **Service name:** `api` (in `docker-compose.yml`)
- **Image:** Built locally from your project’s `Dockerfile`
- **Code location in container:** `/app/src` (copied from your local `./src` directory, plus bind-mounted for live updates in dev)
- **Entrypoint:**  
  ```bash
  uvicorn src.main:app --host 0.0.0.0 --port 8000
  ```
  This means Uvicorn will look for `app` inside `src/main.py`.

---

## **How to access it from your host**
- In `docker-compose.yml`, the `api` service maps:
  ```yml
  ports:
    - "${API_PORT:-8000}:8000"
  ```
  By default, that’s **host port 8000 → container port 8000**.

- So if you haven’t overridden `API_PORT`, you can open:
  ```
  http://localhost:8000
  ```
  in your browser or use `curl`:
  ```bash
  curl http://localhost:8000
  ```

- FastAPI automatically serves interactive API docs at:
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`

---

## **How to access it from other containers in the same network**
- Inside any other service in the `ai-customer-service` network, you can use the service name `api` and port `8000`:
  ```
  http://api:8000
  ```

---

## **How to exec into the container**
If you want to open a shell inside the running app container:
```bash
docker compose exec api /bin/bash
```
or, if bash isn’t installed:
```bash
docker compose exec api sh
```

---

## **Health check**
- Your `Dockerfile` defines:
  ```dockerfile
  HEALTHCHECK CMD curl -fsS http://localhost:8000/health || exit 1
  ```
  So if your app implements `/health`, you can check it directly:
  ```bash
  curl http://localhost:8000/health
  ```

---

If you’d like, I can also walk you through **how to run this stack so the API hot-reloads when you edit your local code** — that way you can develop without rebuilding the image each time. Would you like me to prepare that?
