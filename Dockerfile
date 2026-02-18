FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y \
    git gcc g++ wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
RUN pip install --no-cache-dir --prefix=/install --ignore-installed fastmcp

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y libgomp1 gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/
COPY configs/ ./configs/
COPY examples/ ./examples/
COPY scripts/ ./scripts/
RUN mkdir -p tmp/inputs tmp/outputs jobs results

ENV PYTHONPATH=/app
ENV HF_HOME=/root/.cache

# Pre-download model weights (~6GB) into the final image layer
RUN boltzgen download all

CMD ["python", "src/server.py"]
