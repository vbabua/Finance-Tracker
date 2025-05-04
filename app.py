import streamlit as st
from utils.file_handler import save_temporary_file, delete_temporary_file
from utils.transaction_extractor import extract_transactions_from_pdf, extract_transactions_from_csv
from utils.ui_components import display_transaction_table
from utils.categoriser import categorize_transactions, save_approved_patterns
import os

st.set_page_config(page_title="Finance Tracker", page_icon="💰", layout="wide")

def main():
    st.title("Finance Tracker")

    # Initialize session state for categorization status
    if 'categorization_complete' not in st.session_state:
        st.session_state.categorization_complete = False

    account_type = ""
    extracted_transactions = None
    
    with st.sidebar:
        st.header("Upload Your File")
        uploaded_file = st.file_uploader("Choose a bank statement", type=["pdf", "csv"])

        if uploaded_file is not None:
            # After file upload, ask the user to select the account type
            account_type = st.selectbox(
                "Select Account Type", 
                options=["", "A", "B", "C", "D"],
                index=0
            )

    # Proceed only if an account type is selected  
    if uploaded_file is not None and account_type:
        try:
            temporary_file_path = save_temporary_file(uploaded_file)
            
            st.info("Extracting transactions from the file...")
            
            with st.spinner("Processing..."):
                if account_type == "A":
                    extracted_transactions = extract_transactions_from_pdf(temporary_file_path, debug=False)
                elif account_type == "B":
                    # Implement extraction for account type B
                    st.warning("Extraction for account type B not yet implemented")
                    pass
                elif account_type == "C":
                    extracted_transactions = extract_transactions_from_csv(temporary_file_path, debug=False)
                elif account_type == "D":
                    # Implement extraction for account type D not yet implemented
                    st.warning("Extraction for account type D not yet implemented")
                    pass
                else:
                    st.error("Invalid account type selected.")
                    if os.path.exists(temporary_file_path):
                        delete_temporary_file(temporary_file_path)
                    return
                    
            # Only delete file after successful extraction
            if os.path.exists(temporary_file_path):
                delete_temporary_file(temporary_file_path)
            
            # Check if extraction was successful
            if extracted_transactions is not None and not extracted_transactions.empty:
                st.success("Transactions extracted successfully!")
                
                # Add account type to the dataframe
                extracted_transactions["Account Type"] = account_type
                
                # Toggle for showing raw data
                if st.checkbox("Show raw extracted data", value=False):
                    st.subheader("Raw Extracted Transactions")
                    st.dataframe(extracted_transactions)
                
                # Display formatted transactions
                st.subheader("Extracted Transactions")
                display_transaction_table(extracted_transactions)
                
                # Categorize transactions if extraction was successful and not already categorized
                if not st.session_state.categorization_complete:  # Assuming account type D has categories already
                    try:
                       
                        with st.spinner("Categorizing transactions..."):
                            categorized_df, new_patterns, stats = categorize_transactions(
                                extracted_transactions, account_type
                            )
                            # Mark categorization as complete
                            st.session_state.categorization_complete = True
                            
                        if categorized_df is not None:
                            st.success("Transactions categorized successfully!")
                           
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Transactions", stats["total"])
                            with col2:
                                st.metric("Auto-categorized", f"{stats['pattern_percent']}%")
                            with col3:
                                st.metric("AI-categorized", f"{stats['llm_percent']}%")
                            
                            st.subheader("Categorized Transactions")
                            display_transaction_table(categorized_df)
                    except Exception as e:
                        st.error(f"Error during categorization: {str(e)}")
                        st.session_state.categorization_complete = False
                
                elif st.session_state.categorization_complete:
                    try:
                        categorized_df, new_patterns, stats = categorize_transactions(
                            extracted_transactions, account_type
                        )
                        
                        if categorized_df is not None:
                            st.success("Transactions categorized successfully!")
                            
                            # Show categorization stats
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Transactions", stats["total"])
                            with col2:
                                st.metric("Auto-categorized", f"{stats['pattern_percent']}%")
                            with col3:
                                st.metric("AI-categorized", f"{stats['llm_percent']}%")
                            
                            # Display categorized transactions
                            st.subheader("Categorized Transactions")
                            display_transaction_table(categorized_df)
                    except Exception as e:
                        st.error(f"Error displaying categorized transactions: {str(e)}")
                
                # Create a section for approving new patterns
                if 'new_patterns' in locals() and new_patterns:
                    st.subheader("Review New Patterns")
                    
                    # Store selected patterns in session state
                    if "selected_patterns" not in st.session_state:
                        st.session_state.selected_patterns = [False] * len(new_patterns)
                    elif len(st.session_state.selected_patterns) != len(new_patterns):
                        # Update if number of patterns changed
                        st.session_state.selected_patterns = [False] * len(new_patterns)
                    
                    with st.form("pattern_form"):
                        st.write("The following new merchant patterns were detected. Select which ones to approve:")
                        
                        col1, col2 = st.columns(2)
                        
                        for i, pattern in enumerate(new_patterns):
                            merchant, category = pattern
                    
                            with col1 if i % 2 == 0 else col2:
                                st.session_state.selected_patterns[i] = st.checkbox(
                                    f"{merchant} → {category}", 
                                    value=st.session_state.selected_patterns[i],
                                    key=f"pattern_{i}"
                                )
                        
                        submit_button = st.form_submit_button("Save Approved Patterns")
                        
                    if submit_button:
                     
                        approved_patterns = [
                            new_patterns[i] for i in range(len(new_patterns)) 
                            if st.session_state.selected_patterns[i]
                        ]
                        
                        if approved_patterns:
                            save_approved_patterns(approved_patterns)
                            st.success(f"Saved {len(approved_patterns)} approved patterns!")
                        else:
                            st.warning("No patterns were approved for saving.")
            else:
                st.error("No transactions were extracted from the file. Please check the file format.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()