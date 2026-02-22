FROM node:22.13.1-slim AS aggrid_build

WORKDIR /app

# 1. Build the AG Grid React component
COPY frontend/streamlit_aggrid_range/dragselect/package.json frontend/streamlit_aggrid_range/dragselect/package-lock.json ./dragselect/
RUN cd dragselect \
    && npm install
COPY frontend/streamlit_aggrid_range/dragselect ./dragselect
RUN cd dragselect \
    && npm run build

# 2. Verify the build output exists (fail fast if missing)
RUN test -f /app/dragselect/build/index.html \
    || (echo "ERROR: React build output missing!" && exit 1)

FROM python:3.14-slim

WORKDIR /app

# 3. Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy source
COPY . .

# 5. Copy built React output from temp container
COPY --from=aggrid_build /app/dragselect/build ./frontend/streamlit_aggrid_range/dragselect/build

EXPOSE 8501

CMD ["streamlit", "run", "frontend/home.py", "--server.address=0.0.0.0", "--server.port=8501"]