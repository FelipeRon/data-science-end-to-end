FROM python:3.11.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYSPARK_PYTHON=python \
    SPARK_LOCAL_IP=127.0.0.1 \
    PYTHONPATH=/workspace/kestra:/workspace \
    DBT_PROFILES_DIR=/workspace/dbt
WORKDIR /workspace
COPY kestra/runtime/requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY . .
CMD ["python", "kestra/scripts/run_pipeline.py"]


