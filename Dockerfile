FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update \
	&& apt-get install -y --no-install-recommends nodejs npm \
	&& rm -rf /var/lib/apt/lists/*

RUN cd Frontend/streamlit_aggrid_range/frontend \
	&& npm install \
	&& npm run build

EXPOSE 8501

CMD ["streamlit", "run", "Frontend/homepage.py","--server.address=0.0.0.0","--server.port=8501"]
