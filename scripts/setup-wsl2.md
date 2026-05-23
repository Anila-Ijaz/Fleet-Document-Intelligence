# WSL2 Setup Notes (Windows)

You're running on Windows with WSL2. A few one-time things:

## 1. Install Docker Desktop + enable WSL2 integration
- Install Docker Desktop for Windows.
- In Docker Desktop: Settings → Resources → WSL Integration → enable your distro.
- Verify inside your WSL2 terminal:
  ```bash
  docker --version
  docker compose version
  ```

## 2. Keep the project INSIDE the Linux filesystem
Clone/unzip the project under your WSL2 home (e.g. `~/projects/...`), NOT under
`/mnt/c/...`. Docker file-watching and build speed are dramatically better on the
Linux filesystem.

## 3. Set your OpenAI key
```bash
cp .env.example .env
nano .env          # set OPENAI_API_KEY=sk-...
```

## 4. Run
```bash
docker compose up --build
./scripts/smoke-test.sh
```

Open the API docs from Windows browser at: http://localhost:8000/docs
(WSL2 forwards localhost automatically.)
