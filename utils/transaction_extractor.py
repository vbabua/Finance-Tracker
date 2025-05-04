import pdfplumber
import pandas as pd
import re
from datetime import datetime

def extract_transactions_from_pdf(pdf_path, debug = False):
    """
    Extract transactions from a bank statement file.
    
    Args:
        file_path (str): Path to the bank statement file.
        debug (bool): If True, print debug information.
    
    Returns:
        pd.DataFrame: A DataFrame containing extracted transactions with the following columns:
                      ['Date', 'Details', 'Amount', 'Debit/Credit']
    """
    dates, descriptions, amounts, transaction_types = [], [], [], []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            width, height = page.width, page.height

            # Split the page into left and right halves
            left_part = page.crop((0, 0, width / 2, height))
            right_part = page.crop((width / 2, 0, width, height))
            
            # Extract text from both halves and combine into a list of lines
            page_lines = []
            for part in (left_part, right_part):
                text = part.extract_text()
                if text:
                    page_lines.extend(text.split("\n"))
            
            # Skip the first page (usually the summary)
            if page_num == 0:
                continue
            
            # Process each line to extract transaction details
            for line in page_lines:

                # Skip header/footer lines that are not transactions
                if any(skip_word in line for skip_word in [
                    "Page", 
                    "Your transactions", 
                    "Your previous balance", 
                    "Payments towards your account", 
                    "Understanding your interest"
                ]):
                    continue
                
                # Try to find a date at the start of the line
                date_match = re.match(r'^(\d{1,2}\s+[A-Za-z]{3})', line)

                # Try to find an amount somewhere in the line
                amount_match = re.search(r'(-?£[\d,]+\.\d{2}(?:CR)?)', line)

                if date_match and amount_match:
                    date_str = date_match.group(1)

                    # Extract and clean the amount
                    amount_text = amount_match.group(1)
                    amount_clean = float(amount_text.replace('CR', '').replace('£', '').replace(',', ''))
    
                    # Extract the transaction description
                    start_idx = len(date_match.group(0))
                    end_idx = line.rfind(amount_text)
                    description = line[start_idx:end_idx].strip() if end_idx > start_idx else "Unknown"

                    transaction_type = "Credit" if "CR" in amount_text or "payment" in description.lower() else "Debit"
                    if amount_text.startswith('-'):
                        transaction_type = "Debit"

                    year = datetime.now().year
                    date_obj = datetime.strptime(f"{date_str} {year}", "%d %b %Y")
                    
                    dates.append(date_obj.strftime("%Y-%m-%d"))
                    descriptions.append(description)
                    amounts.append(amount_clean)
                    transaction_types.append(transaction_type)

    if debug:
        print(f"Extracted {len(dates)} transactions")

    # Create DataFrame from extracted data
    df = pd.DataFrame({
        "Date": dates,
        "Details": descriptions,
        "Amount": amounts,
        "Debit/Credit": transaction_types
    })

    df["Date"] = pd.to_datetime(df["Date"])

    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.strftime("%B")

    df["Date"] = df["Date"].dt.strftime('%Y-%m-%d')

    df = df[["Date", "Year", "Month", "Details", "Amount", "Debit/Credit"]]

    return df

def extract_transactions_from_csv(csv_path, debug = False):
    """
    Extracts transactions from a Revolut CSV statement.

    Args:
        csv_path (str): Path to the uploaded Revolut CSV statement.

    Returns:
        pd.DataFrame: A DataFrame containing formatted transactions matching the expected format
    """
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Create a new DataFrame with the required columns
    transactions_df = pd.DataFrame()
    
    # Extract and transform data
    transactions_df["Date"] = pd.to_datetime(df["Completed Date"]).dt.strftime('%Y-%m-%d')
    transactions_df["Details"] = df["Description"]
    transactions_df["Amount"] = df["Amount"].abs()  # Remove negative sign, we'll handle type separately
    
    # Determine transaction type (Credit or Debit)
    transactions_df["Debit/Credit"] = df["Amount"].apply(
        lambda x: "Credit" if x >= 0 else "Debit"
    )
    
    # Add year and month columns
    transactions_df["Year"] = pd.to_datetime(df["Completed Date"]).dt.year
    transactions_df["Month"] = pd.to_datetime(df["Completed Date"]).dt.strftime("%B")
    
    # Reorder columns to match expected format
    transactions_df = transactions_df[["Date", "Year", "Month", "Details", "Amount", "Debit/Credit"]]
    
    return transactions_df