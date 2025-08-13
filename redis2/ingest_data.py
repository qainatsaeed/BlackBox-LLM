#!/usr/bin/env python3
"""
Simple CSV Ingestion Script for HR Data
"""
import pandas as pd
import json
import redis
import time
import os
import sys

def ingest_csv_files():
    """Ingest CSV files and put sample queries in Redis"""
    try:
        # Connect to Redis
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Test Redis connection
        redis_client.ping()
        print("✅ Connected to Redis")
        
        # Read CSV files
        sales_file = "dailySalesBreakdown.csv"
        schedule_file = "file1.csv"
        
        if os.path.exists(sales_file):
            df_sales = pd.read_csv(sales_file)
            print(f"✅ Loaded sales data: {len(df_sales)} rows")
        else:
            print(f"❌ Sales file not found: {sales_file}")
            
        if os.path.exists(schedule_file):
            df_schedule = pd.read_csv(schedule_file)
            print(f"✅ Loaded schedule data: {len(df_schedule)} rows")
        else:
            print(f"❌ Schedule file not found: {schedule_file}")
        
        # Store sample data in Redis for testing
        sample_data = {
            "sales_summary": {
                "total_days": len(df_sales) if 'df_sales' in locals() else 0,
                "sample_date": str(df_sales.iloc[0]['Shifts\nDate']) if 'df_sales' in locals() and len(df_sales) > 0 else None
            },
            "employee_summary": {
                "total_records": len(df_schedule) if 'df_schedule' in locals() else 0,
                "unique_employees": len(df_schedule['Employee'].unique()) if 'df_schedule' in locals() else 0
            }
        }
        
        redis_client.set("hr_data_summary", json.dumps(sample_data))
        print("✅ Stored summary data in Redis")
        
        # Add sample queries to the ask queue
        sample_queries = [
            {
                "question": "How many employees worked in May 2025?",
                "user_id": "test_user",
                "role": "manager",
                "location": "RT2 - South Austin",
                "timestamp": time.time()
            },
            {
                "question": "What was the total sales for the first week of May?",
                "user_id": "test_user",
                "role": "manager", 
                "location": "RT2 - South Austin",
                "timestamp": time.time()
            }
        ]
        
        for query in sample_queries:
            redis_client.rpush("hrask.ask.queue", json.dumps(query))
            
        print(f"✅ Added {len(sample_queries)} sample queries to ask queue")
        print("🚀 Ingestion complete!")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ingest_csv_files()
