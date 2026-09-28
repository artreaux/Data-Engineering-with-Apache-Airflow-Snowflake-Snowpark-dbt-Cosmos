# syntax=quay.io/astronomer/airflow-extensions:latest

FROM quay.io/astronomer/astro-runtime:9.1.0-python-3.9-base

USER root
RUN sed -i '/debian-security/d' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true; \
    sed -i 's|deb.debian.org/debian |archive.debian.org/debian |g' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true; \
    apt-get update -o Acquire::Check-Valid-Until=false \
    && apt-get install -y --no-install-recommends build-essential libre2-dev libabsl-dev pybind11-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY include/astro_provider_snowflake-0.0.0-py3-none-any.whl /tmp

ENV PIP_ONLY_BINARY=google-re2
# Create the virtual environment
PYENV 3.10 snowpark requirements-snowpark.txt

RUN python -m venv dbt_venv && source dbt_venv/bin/activate && pip install --no-cache-dir dbt-core dbt-snowflake && pip install --no-cache-dir dbt-postgres && deactivate