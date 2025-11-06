#!/usr/bin/env python3
"""
Clean the dailySalesBreakdown.csv file to remove header rows and format properly
"""
import pandas as pd
import os

def clean_sales_csv():
    """Clean and reformat the sales CSV file"""
    input_file = "/Users/asjad/Development/q/anthony/BlackBox-LLM/redis2/redis2/dailySalesBreakdown.csv"
    output_file = "/Users/asjad/Development/q/anthony/BlackBox-LLM/redis2/redis2/dailySalesBreakdown_cleaned.csv"
    
    # Read the raw CSV
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Find the actual data start (skip header rows)
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith("Shifts"):
            data_start = i
            break
    
    # Read from the data start
    df = pd.read_csv(input_file, skiprows=data_start)
    
    # Remove completely empty rows
    df = df.dropna(how='all')
    
    # Reset index
    df = df.reset_index(drop=True)
    
    print(f"Cleaned CSV shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    # Save cleaned version
    df.to_csv(output_file, index=False)
    print(f"\nCleaned file saved to: {output_file}")
    
    # Also backup the original and replace it
    backup_file = input_file + ".backup"
    os.rename(input_file, backup_file)
    os.rename(output_file, input_file)
    print(f"Original backed up to: {backup_file}")
    print(f"Cleaned file moved to: {input_file}")

if __name__ == "__main__":
    clean_sales_csv()
