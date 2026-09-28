import os

import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Hotel Booking Analytics", layout="wide")
st.title("🏨 Hotel Booking Analytics Dashboard")

# ---- Snowflake connection -------------------------------------------------
# Reads credentials from environment variables (set these in your .env file,
# in the project root, one directory above include/).
#
#   SNOWFLAKE_ACCOUNT=your_account_identifier
#   SNOWFLAKE_USER=dbt_user
#   SNOWFLAKE_PASSWORD=your_password
#   SNOWFLAKE_WAREHOUSE=dbt_dev_wh
#   SNOWFLAKE_ROLE=dbt_dev_role
#   SNOWFLAKE_DATABASE=demo_dbt
#
# Optional, for the Q&A section at the bottom:
#   OPENAI_API_KEY=sk-...


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        database=os.getenv("SNOWFLAKE_DATABASE", "DEMO_DBT"),
    )


@st.cache_data(ttl=600)
def load_table(fully_qualified_table: str) -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {fully_qualified_table}")
        return cur.fetch_pandas_all()


# ---- Load data --------------------------------------------------------
# Adjust these fully-qualified names if your dbt schemas/table names differ
# from the ones set in dbt_project.yml (models.cosmosproject.analysis.schema).
try:
    hotel_counts = load_table("PUBLIC.HOTEL_COUNT_BY_DAY")
    avg_cost = load_table("PUBLIC.THIRTY_DAY_AVG_COST")
except Exception as exc:  # noqa: BLE001
    st.error(
        "Could not load data from Snowflake. Check your .env credentials "
        f"and that the tables exist. Details: {exc}"
    )
    st.stop()

# ---- Charts -------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Bookings per Day")
    if not hotel_counts.empty:
        st.bar_chart(hotel_counts.set_index(hotel_counts.columns[0]))
    else:
        st.info("No data returned for HOTEL_COUNT_BY_DAY.")

with col2:
    st.subheader("30-Day Average Cost by Hotel")
    if {"HOTEL", "COST"}.issubset(avg_cost.columns):
        st.bar_chart(avg_cost.set_index("HOTEL")["COST"])
    else:
        st.dataframe(avg_cost)

# ---- Highlight the most expensive hotel, same as the findbesthotel task --
if {"HOTEL", "COST"}.issubset(avg_cost.columns) and not avg_cost.empty:
    top_row = avg_cost.loc[avg_cost["COST"].idxmax()]
    st.metric(
        label="Highest 30-day average cost",
        value=str(top_row["HOTEL"]),
        delta=f"${top_row['COST']:.2f}",
    )

# ---- Raw data tables ------------------------------------------------------
st.subheader("Raw Data")
tab1, tab2 = st.tabs(["Hotel Count by Day", "30-Day Avg Cost"])
with tab1:
    st.dataframe(hotel_counts)
with tab2:
    st.dataframe(avg_cost)

# ---- Optional: ask questions about the data via OpenAI --------------------
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    from openai import OpenAI

    client = OpenAI(api_key=openai_key)

    st.subheader("💬 Ask a question about your data")
    question = st.text_input("Your question")
    if question:
        context = (
            "Hotel count by day:\n"
            f"{hotel_counts.to_string(index=False)}\n\n"
            "30-day average cost by hotel:\n"
            f"{avg_cost.to_string(index=False)}"
        )
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a data analyst assistant. Answer "
                            "questions using only the data provided below."
                        ),
                    },
                    {"role": "user", "content": f"Data:\n{context}\n\nQuestion: {question}"},
                ],
            )
        st.write(response.choices[0].message.content)
else:
    st.info("Add an OPENAI_API_KEY to your .env file to enable Q&A about your data.")