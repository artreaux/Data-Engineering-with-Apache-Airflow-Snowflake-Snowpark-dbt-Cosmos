# dbt + Airflow (Astro) + Snowflake + Snowpark + Streamlit (Updated for 09/28/2026) Resolved deprecated dependencies, etc. 


Hotel booking analytics pipeline based on Snowflake's *Data Engineering with Apache Airflow* guide, updated to work with current tooling.

```
CSV seeds -> dbt models (Cosmos in Airflow) -> Snowflake tables
          -> Snowpark task (findbesthotel) -> Streamlit dashboard
```

## Project layout

```
dags/
  dbt/cosmosproject/        dbt project (seeds/, models/, dbt_project.yml)
  my_cosmos_dag.py          DbtDag: seeds + models
  cosmosandsnowflake.py     DbtTaskGroup + Snowpark task
include/
  astro_provider_snowflake-0.0.0-py3-none-any.whl
  streamlit/src/streamlit_app.py
Dockerfile
requirements.txt            main Airflow env (Python 3.9)
requirements-snowpark.txt   Snowpark venv (Python 3.10)
packages.txt                empty (see Dockerfile)
docker-compose.override.yml exposes Streamlit on 8501
.env.example                copy to .env and fill in
```

## Setup

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and the [Astro CLI](https://www.astronomer.io/docs/astro/cli/install-cli).
2. Copy `.env.example` to `.env` and fill in real Snowflake credentials. **Never commit `.env`.**
3. In Snowflake, make sure the role in `.env` (e.g. `dbt_dev_role`) has access to the database:
   ```sql
   GRANT USAGE ON DATABASE demo_dbt TO ROLE dbt_dev_role;
   GRANT USAGE ON ALL SCHEMAS IN DATABASE demo_dbt TO ROLE dbt_dev_role;
   GRANT CREATE SCHEMA ON DATABASE demo_dbt TO ROLE dbt_dev_role;
   ```
4. `astro dev start`, then open http://localhost:8080 (default login `admin` / `admin`).
5. In Airflow: Admin > Connections > add `snowflake_default` (type Snowflake: login, password, account, warehouse, role).
6. Trigger `dbt_snowflake_dag` and `dbt_snowpark`.
7. Dashboard:
   ```bash
   astro dev bash -w
   cd include/streamlit/src
   python -m streamlit run ./streamlit_app.py
   ```
   Then open http://localhost:8501.

## Key configuration

**Dockerfile**
```dockerfile
# syntax=quay.io/astronomer/airflow-extensions:latest
FROM quay.io/astronomer/astro-runtime:9.1.0-python-3.9-base

USER root
RUN sed -i '/debian-security/d' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true; \
    sed -i 's|deb.debian.org/debian |archive.debian.org/debian |g' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true; \
    apt-get update -o Acquire::Check-Valid-Until=false \
    && apt-get install -y --no-install-recommends build-essential libre2-dev libabsl-dev pybind11-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY include/astro_provider_snowflake-0.0.0-py3-none-any.whl /tmp

ENV PIP_ONLY_BINARY=google-re2
PYENV 3.10 snowpark requirements-snowpark.txt

RUN python -m venv dbt_venv && source dbt_venv/bin/activate && pip install --no-cache-dir dbt-core dbt-snowflake dbt-postgres && deactivate
```

**requirements.txt**
```
astronomer-cosmos
apache-airflow-providers-snowflake==4.0.4
/tmp/astro_provider_snowflake-0.0.0-py3-none-any.whl
setuptools<71
streamlit
python-dotenv
openai
```

**requirements-snowpark.txt**
```
psycopg2-binary
snowflake_snowpark_python[pandas]==1.5.1
virtualenv
apache-airflow-providers-snowflake==4.0.4
/tmp/astro_provider_snowflake-0.0.0-py3-none-any.whl
```

**docker-compose.override.yml**
```yaml
services:
  webserver:
    ports:
      - 8501:8501
```

**dbt_project.yml** (relevant lines)
```yaml
seed-paths: ["seeds"]
target-path: "target"      # must be a string, not a list
```

**Snowpark task decorator** (`cosmosandsnowflake.py`)
```python
@task.snowpark_virtualenv(
    python_version='3.10',
    requirements=['snowflake-ml-python==1.0.9',
                  '/tmp/astro_provider_snowflake-0.0.0-py3-none-any.whl'],
)
```

## Issues hit and how they were fixed

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 1 | `dbt init` had no name prompt; `dbt init cosmosproject` failed with "unexpected argument" | The `dbt` on PATH was dbt Fusion (Rust CLI), not dbt-core | Use dbt-core (`pip install dbt-core dbt-snowflake`). Never install the bare `dbt` package. |
| 2 | Airflow login prompt | Astro creates a default user | `admin` / `admin` |
| 3 | `Broken plugin: cannot import name 'parse_version' from 'pkg_resources'` | Newer setuptools removed the API that cosmos/openlineage use | `setuptools<71` in `requirements.txt` |
| 4 | `exampledag.py`: `No module named 'airflow.sdk'` | Stock example DAG written for Airflow 3 | Delete `dags/exampledag.py` |
| 5 | `Could not find dbt_project.yml` | dbt project was outside the Astro project | Move it to `dags/dbt/cosmosproject/` |
| 6 | `dbt ls` failed with `SerializationError (dbt1013)` and `dbt 2.0.0-alpha` in the log | Fusion had been pulled into `dbt_venv` (regressed later when `dbt-core` was dropped from the pip line) | Install `dbt-core` explicitly in the Dockerfile venv line |
| 7 | `ref('bookings_1') not found` | CSVs were in a `data/` folder; dbt only reads `seeds/` by default | Put CSVs in `seeds/` |
| 8 | SSL hostname mismatch to Snowflake | Account identifier had a malformed region (`ap.northeast-1`) | Use the correct account identifier from Snowsight |
| 9 | `Object does not exist ... listing schemas in database` | `dbt_dev_role` lacked grants on the database | Grants shown in Setup step 3; set Role in the Airflow connection |
| 10 | `KeyError: 'target-path'` after dbt succeeded | Cosmos/OpenLineage reads `dbt_project.yml` as raw YAML | Add `target-path: "target"` (string, not list) |
| 11 | Docker build: `include/astro_provider_snowflake...whl not found` | Wheel was in the project root | Move it into `include/` |
| 12 | `apt-get` 404s from `bullseye-security` | Debian 11 LTS ended Aug 31, 2026 | Drop the security repo line and point apt at `archive.debian.org` (Dockerfile RUN block) |
| 13 | `google-re2` failed to compile (absl, pybind11 headers), then build hung 90+ min | No Python 3.8 wheel for the required version; source build needs newer libs than bullseye has | Move Snowpark venv to Python 3.10; remove the duplicate `pip install` block; `PIP_ONLY_BINARY=google-re2` |
| 14 | `TypeError: 'dict' object is not callable` in `snowpark.py` | Custom wheel calls `_get_conn_params()`, which is a property in newer provider versions | Pin `apache-airflow-providers-snowflake==4.0.4` |
| 15 | `failed to find interpreter for python3.8` | Python 3.8 no longer in the image | `python_version='3.10'` in the decorator |
| 16 | `No module named 'astronomer'` inside the task venv | Ephemeral venv doesn't inherit the wheel | List the wheel in the decorator's `requirements` |
| 17 | Streamlit `ERR_CONNECTION_REFUSED` | Port 8501 not published | `docker-compose.override.yml`, then `astro dev restart` |
| 18 | `KeyError: 'SNOWFLAKE_ACCOUNT'` | Every line in `.env` was commented out with `#` | Uncomment, fill in, `astro dev restart` |
| 19 | Dashboard charts looked wrong | Charts didn't match the table shape | Pivot bookings by date and hotel; aggregate cost per hotel |

## Notes

- **Untested:** the `build-essential`, `libre2-dev`, `libabsl-dev` and `pybind11-dev` packages were added while debugging the Python 3.8 build. They may no longer be needed on Python 3.10. Try removing them (and the `archive.debian.org` block) to speed up builds.
- **Stale tooling:** the guide pins old versions (Airflow 2.x runtime 9.1.0, Snowpark 1.5.1, `snowflake-ml-python==1.0.9`). Debian 11 is now end-of-life, so upgrading the Astro Runtime base image is the long-term fix.
- **Cosmos + dbt Fusion:** Cosmos targets dbt-core. Keep Fusion out of `dbt_venv`.
