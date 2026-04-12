FROM node:22.13.1-slim AS aggrid_build

WORKDIR /app

# 1. Build the AG Grid React component
COPY Frontend/streamlit_aggrid_range/dragselect/package.json Frontend/streamlit_aggrid_range/dragselect/package-lock.json ./dragselect/
RUN cd dragselect \
    && npm install
COPY Frontend/streamlit_aggrid_range/dragselect ./dragselect
RUN cd dragselect \
    && npm run build

# 2. Verify the build output exists (fail fast if missing)
RUN test -f /app/dragselect/build/index.html \
    || (echo "ERROR: React build output missing!" && exit 1)

FROM python:3.14-rc-slim

WORKDIR /app

# 3. System libraries required by kaleido's bundled Chromium binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 4. Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy source
COPY . .

# 6. Copy built React output from temp container
COPY --from=aggrid_build /app/dragselect/build ./Frontend/streamlit_aggrid_range/dragselect/build

EXPOSE 8501

CMD ["streamlit", "run", "Frontend/home.py", "--server.address=0.0.0.0", "--server.port=8501"]