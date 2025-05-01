import streamlit as st
from utils.file_handler import save_temporary_file, delete_temporary_file

st.set_page_config(page_title="Finance Tracker", page_icon="💰", layout="wide")

def main():
    st.title("Finance Tracker")

    with st.sidebar:
        st.header("Upload Your File")

    uploaded_file = st.file_uploader("Choose a bank statement", type=["pdf", "csv"])

    if uploaded_file is not None:
        # After file upload, ask the user to select the accoutn type
        with st.sidebar:
            account_name = st.selectbox(
                "Select Account Type", 
                options = ["", "A", "B", "C", "D"],
                index = 0
            )

    # Proceed only if an account type is selected  
    if account_name:
        temporary_file_path = save_temporary_file(uploaded_file)

        st.success(f"File saved temporarily at: {temporary_file_path}")

        st.info("Extracting transactions from the file...")

        with st.spinner("Extracting transactions..."):
            if account_name == "A":
                # Call the function to extract transactions for account A
                pass
            elif account_name == "B":
                # Call the function to extract transactions for account B
                pass
            elif account_name == "C":
                # Call the function to extract transactions for account C
                pass
            elif account_name == "D":
                # Call the function to extract transactions for account D
                pass
            else:
                st.error("Invalid account type selected.")
                return
        delete_temporary_file(temporary_file_path)
        st.success("Transactions extracted successfully!")