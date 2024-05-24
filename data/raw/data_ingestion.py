# data/raw/data_ingestion.py

import os
import pandas as pd

def ingest_data(file_path):
    """
    Ingests raw data from a CSV file and returns a pandas DataFrame.
    
    Args:
        file_path (str): Path to the raw data CSV file.
        
    Returns:
        pandas.DataFrame: DataFrame containing the ingested raw data.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        data = pd.read_csv(file_path)
        return data
    except pd.errors.EmptyDataError:
        raise ValueError(f"Empty data file: {file_path}")
    except pd.errors.ParserError:
        raise ValueError(f"Invalid data format in file: {file_path}")