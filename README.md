# seniordesign


## Build Instructions
docker build -t senior-design-app:1.0 .


## Run Instructions

### Option A — Docker Compose (recommended)
Automatically applies all volume mounts, including results_cache:
```
docker compose up
```

### Option B — docker run
Pass the bind mount manually so results_cache is persisted to your host:
```
docker run --rm -p 8501:8501 -v "%cd%\results_cache:/app/results_cache" senior-design-app:1.0
```
On PowerShell:
```
docker run --rm -p 8501:8501 -v "${PWD}\results_cache:/app/results_cache" senior-design-app:1.0
```

The `results_cache/` folder will be created automatically on first run and persists across container restarts and rebuilds.
