# src/data_ingestion/data_ingestion.py

import os
import pandas as pd
from typing import List
from sqlalchemy import create_engine

class DataIngestion:
    def __init__(self, data_path: str, db_connection_string: str):
        self.data_path = data_path
        self.db_connection_string = db_connection_string
        self.engine = create_engine(db_connection_string)

    def read_csv_files(self, file_names: List[str]) -> pd.DataFrame:
        """
        Read multiple CSV files and concatenate them into a single DataFrame.
        
        Args:
            file_names: List of CSV file names to be read.
        
        Returns:
            Concatenated DataFrame containing data from all the CSV files.
        """
        dataframes = []
        for file_name in file_names:
            file_path = os.path.join(self.data_path, file_name)
            df = pd.read_csv(file_path)
            dataframes.append(df)
        
        concatenated_df = pd.concat(dataframes, ignore_index=True)
        return concatenated_df

    def write_to_database(self, dataframe: pd.DataFrame, table_name: str):
        """
        Write the DataFrame to the specified database table.
        
        Args:
            dataframe: DataFrame to be written to the database.
            table_name: Name of the table in the database.
        """
        dataframe.to_sql(table_name, self.engine, if_exists='replace', index=False)
        print(f"Data ingested successfully into table: {table_name}")

    def run_ingestion_pipeline(self, file_names: List[str], table_name: str):
        """
        Run the data ingestion pipeline.
        
        Args:
            file_names: List of CSV file names to be ingested.
            table_name: Name of the table in the database.
        """
        dataframe = self.read_csv_files(file_names)
        self.write_to_database(dataframe, table_name)
