FROM python:3.14-slim

WORKDIR /app

# 1. Install Node 22 (pinned) — must come before npm build
RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl ca-certificates xz-utils \
	&& curl -fsSL https://nodejs.org/dist/v22.13.1/node-v22.13.1-linux-x64.tar.xz \
	   -o /tmp/node.tar.xz \
	&& tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
	&& rm /tmp/node.tar.xz \
	&& apt-get purge -y --auto-remove curl xz-utils \
	&& rm -rf /var/lib/apt/lists/*

# 2. Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy source
COPY . .

# 4. Build the AG Grid React component
RUN cd Frontend/streamlit_aggrid_range/frontend \
	&& npm install \
	&& npm run build

# 5. Verify the build output exists (fail fast if missing)
RUN test -f Frontend/streamlit_aggrid_range/frontend/build/index.html \
	|| (echo "ERROR: React build output missing!" && exit 1)

EXPOSE 8501

CMD ["streamlit", "run", "Frontend/homepage.py", "--server.address=0.0.0.0", "--server.port=8501"]
