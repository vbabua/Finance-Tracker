# improved_categorizer.py
import json
import os
import pandas as pd
import re
from langchain_ollama import OllamaLLM
from loguru import logger

# Configure Loguru
logger.remove()  # Remove the default handler
logger.add("finance_tracker.log", rotation="10 MB", level="INFO")  # Add a file handler

def load_categories(file_path="categories.json"):
    """Load category mappings from JSON file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)

def categorize_with_llm(text, account_type, llm_model="llama2"):
    """Use LLM to categorize a transaction."""
    llm = OllamaLLM(model=llm_model)
    
    account_context = ""
    if account_type == "Barclays Credit Card":
        account_context = "Note: For credit cards, 'payment' usually means paying the credit card bill."
    elif account_type == "Revolut":
        account_context = "Note: For Revolut, 'payment' usually refers to a purchase."
    
    prompt = f"""
    Categorize this transaction into ONE of these categories:
    - Rent
    - Home Utilities
    - Groceries
    - Transportation
    - Dining Out
    - Entertainment
    - Clothing
    - Shopping
    - Health
    - Travel
    - Productivity
    - AI Subscriptions
    - Subscriptions
    - Income
    - Transfers
    - Miscellaneous

    Transaction: {text}
    Account type: {account_type}
    {account_context}

    Category:
    """
    
    response = llm.invoke(prompt).strip()

    valid_categories = [
        "Housing", "Utilities", "Groceries", "Transportation", 
        "Dining Out", "Entertainment", "Shopping", "Health",
        "Travel", "Subscriptions", "Income", "Transfers", "Miscellaneous"
    ]
    
    for category in valid_categories:
        if category.lower() in response.lower():
            return category
    
    return "Miscellaneous"

def extract_merchant(text):
    """Extract merchant name from transaction description."""
    if not isinstance(text, str):
        return ""
        
    text = text.lower()
    for prefix in ["card payment to ", "payment to ", "direct debit "]:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    return text.split(" on ")[0].split(" ref ")[0].strip()

def save_approved_patterns(approved_patterns, categories_file="categories.json"):
    """
    Save only approved patterns to the categories file.
    
    Args:
        approved_patterns (list): List of (merchant, category) tuples to approve
        categories_file (str): Path to categories JSON file
    """

    with open(categories_file, "r") as f:
        categories = json.load(f)
    
    for merchant, category in approved_patterns:
        categories["learned_patterns"][merchant] = category

    with open(categories_file, "w") as f:
        json.dump(categories, f, indent=2)
    
    return categories

def categorize_transactions(df, account_type, categories_file="categories.json", llm_model="gemma3"):
    """
    Categorize all transactions in a dataframe.
    
    Args:
        df (pd.DataFrame): DataFrame with transactions
        account_type (str): The type of account
        categories_file (str): Path to categories JSON file
        llm_model (str): Name of the LLM model to use
        
    Returns:
        tuple: (DataFrame with categories, list of new category mappings)
    """
    categories = load_categories(categories_file)
    
    if 'Category' not in df.columns:
        df['Category'] = None

    new_patterns = []

    uncategorized_mask = df['Category'].isna()
   
    logger.info("PASS 1: Checking account-specific terms")

    if account_type in categories["account_terms"]:
        for term, category in categories["account_terms"][account_type].items():
            term_mask = df['Details'].str.strip().str.lower() == term.lower()

            matches = term_mask.sum()

            if matches > 0:
                logger.info(f"  Exact match: '{term}' → '{category}', {matches} transactions")
                for idx in df[term_mask].index:
                    logger.info(f"    Transaction {idx}: '{df.at[idx, 'Details']}' → '{category}'")
                df.loc[term_mask, 'Category'] = category

            contains_mask = df['Details'].str.lower().str.contains(term, na=False) & uncategorized_mask
            matches = contains_mask.sum()
            if matches > 0:
                logger.info(f"  Partial match: '{term}' → '{category}', {matches} transactions")
                for idx in df[contains_mask].index:
                    logger.info(f"    Transaction {idx}: '{df.at[idx, 'Details']}' → '{category}'")
                df.loc[contains_mask, 'Category'] = category
        
        uncategorized_mask = df['Category'].isna()
        logger.info(f"After account-specific terms: {uncategorized_mask.sum()} uncategorized")
    
    logger.info("PASS 2: Checking learned patterns")
    learned_patterns_count = 0
    if categories["learned_patterns"]:
        for merchant, category in categories["learned_patterns"].items():
            merchant_mask = df['Details'].str.lower().str.contains(merchant, na=False) & uncategorized_mask
            matches = merchant_mask.sum()
            if matches > 0:
                logger.info(f"  Learned pattern match: '{merchant}' → '{category}', {matches} transactions")
                for idx in df[merchant_mask].index:
                    logger.info(f"    Transaction {idx}: '{df.at[idx, 'Details']}' → '{category}'")
                df.loc[merchant_mask, 'Category'] = category
                learned_patterns_count += matches
        
        uncategorized_mask = df['Category'].isna()
        logger.info(f"After learned patterns: {uncategorized_mask.sum()} uncategorized, {learned_patterns_count} matched")

    logger.info("PASS 3: Checking predefined category patterns")
    category_patterns_count = 0
    for category, patterns in categories["categories"].items():
        if not patterns:
            continue
            
        escaped_patterns = [re.escape(pattern.lower()) for pattern in patterns]
        
        pattern_str = '|'.join(escaped_patterns)
        
        pattern_mask = df['Details'].str.lower().str.contains(pattern_str, na=False, regex=True) & uncategorized_mask
        match_count = pattern_mask.sum()
        
        if match_count > 0:
            logger.info(f"  Category '{category}': {match_count} matches")
            for idx in df[pattern_mask].index:
                logger.info(f"    Transaction {idx}: '{df.at[idx, 'Details']}' → '{category}'")
            df.loc[pattern_mask, 'Category'] = category
            category_patterns_count += match_count
            
        uncategorized_mask = df['Category'].isna()
    
    logger.info(f"After category patterns: {uncategorized_mask.sum()} uncategorized, {category_patterns_count} matched")
    
    logger.info("PASS 4: Using LLM for remaining uncategorized transactions")
    llm_usage_count = 0
    
    for idx, row in df[uncategorized_mask].iterrows():
        description = str(row['Details']) if pd.notna(row['Details']) else ""
        
        if not description.strip():
            logger.info(f"  Transaction {idx}: Empty description → 'Miscellaneous'")
            df.at[idx, 'Category'] = "Miscellaneous"
            continue
        
        logger.info(f"  Using LLM for transaction {idx}: '{description}'")
        category = categorize_with_llm(description, account_type, llm_model)
        logger.info(f"    LLM categorization: '{description}' → '{category}'")
        df.at[idx, 'Category'] = category
        llm_usage_count += 1
        
        if category != "Miscellaneous":
         
            merchant = extract_merchant(description)
            if merchant and len(merchant) > 3:
                logger.info(f"    Adding new pattern: '{merchant}' → '{category}'")
                categories["learned_patterns"][merchant] = category
                new_patterns.append((merchant, category))
    
    total = len(df)
    llm_count = llm_usage_count
    pattern_count = total - llm_count
    
    stats = {
        "total": total,
        "pattern_count": pattern_count,
        "pattern_percent": round(pattern_count / total * 100, 1) if total > 0 else 0,
        "llm_count": llm_count,
        "llm_percent": round(llm_count / total * 100, 1) if total > 0 else 0,
        "new_patterns": len(new_patterns)
    }
    
    logger.info(f"Categorization complete: {stats}")
    
    return df, new_patterns, stats