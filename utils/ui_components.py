import streamlit as st
import pandas as pd

def display_transaction_table(transactions_df):
    """
    Display a table of transactions in Streamlit.
    
    Args:
        transactions_df (pd.DataFrame): DataFrame containing transaction data.
    """
    st.subheader("Transaction Table")
    
    display_df = transactions_df.copy()

    display_df["Transaction #"] = range(1, len(display_df) + 1)

    columns = ["Transaction #"] + [column for column in display_df.columns if column != "Transaction #"]
    display_df = display_df[columns]

    if 'Amount' in display_df.columns:
        display_df["Amount"] = display_df["Amount"].apply(lambda x: f"£{x:,.2f}")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

