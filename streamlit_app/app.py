"""S00 Day 3 smoke test — verify Streamlit can read from Neon.

Disposable. Proves the deployment path before any real dashboard is built.
"""

import os

import pandas as pd
import psycopg
import streamlit as st

st.set_page_config(page_title="Credit Risk — Connection Test", layout="wide")


def get_database_url() -> str:
    """Return the Neon URL from Streamlit secrets, falling back to .env."""
    try:
        return st.secrets["NEON_DATABASE_URL"]
    except Exception:
        pass

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("NEON_DATABASE_URL")
    if not url:
        raise ValueError("NEON_DATABASE_URL not found in secrets or .env")
    return url


@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    """Read the test table from Neon."""
    with psycopg.connect(get_database_url()) as conn:
        return pd.read_sql_query(
            "SELECT * FROM test_loan_sample ORDER BY loan_id LIMIT 500;", conn
        )


st.title("Credit Risk Portfolio — Infrastructure Smoke Test")
st.caption("S00 Day 3. Synthetic data. Verifies Streamlit → Neon PostgreSQL.")

try:
    df = load_data()

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows returned", f"{len(df):,}")
    col2.metric("Mean credit score", f"{df['credit_score'].mean():.0f}")
    col3.metric("Mean LTV", f"{df['ltv'].mean():.1f}%")

    st.subheader("Loans by state")
    st.bar_chart(df["property_state"].value_counts())

    st.subheader("Sample records")
    st.dataframe(df.head(50), use_container_width=True)

    st.success("Connection to Neon confirmed.")

except Exception as exc:
    st.error(f"Connection failed: {exc}")
