# src/data_ingestion/data_ingestion.py

import os
import pandas as pd
from sqlalchemy import create_engine, Table, Column, Integer, Float, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class DataIngestion:
    def __init__(self, data_path: str, db_connection_string: str):
        self.data_path = data_path
        self.db_connection_string = db_connection_string
        self.engine = create_engine(db_connection_string)
        print(f"Database engine created with connection string: {db_connection_string}")
        self.metadata = MetaData()

    def read_csv_file(self, file_name: str) -> pd.DataFrame:
        """
        Read a single CSV file and return a DataFrame.
        
        Args:
            file_name: Name of the CSV file to be read.
        
        Returns:
            DataFrame containing data from the CSV file.
        """
        file_path = os.path.join(self.data_path, file_name)
        print(f"Reading CSV file from: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            return df
        except pd.errors.EmptyDataError:
            raise ValueError(f"Empty data file: {file_path}")
        except pd.errors.ParserError:
            raise ValueError(f"Invalid data format in file: {file_path}")

    def write_to_database(self, dataframe: pd.DataFrame, table_name: str):
        """
        Write the DataFrame to the specified database table using SQLAlchemy core.
        
        Args:
            dataframe: DataFrame to be written to the database.
            table_name: Name of the table in the database.
        """
        try:
            print(f"Writing DataFrame to database table: {table_name}")
            
            # Reflect existing tables
            self.metadata.reflect(bind=self.engine)
            if table_name in self.metadata.tables:
                table = self.metadata.tables[table_name]
            else:
                table = Table(table_name, self.metadata,
                              *[Column(col, String) for col in dataframe.columns])
                self.metadata.create_all(self.engine)

            # Insert data
            with self.engine.connect() as connection:
                connection.execute(table.delete())  # Clear existing data
                connection.execute(table.insert(), dataframe.to_dict(orient='records'))
                
            print(f"Data ingested successfully into table: {table_name}")
        except SQLAlchemyError as e:
            raise ValueError(f"Error writing to database: {str(e)}")

    def run_ingestion_pipeline(self, file_name: str, table_name: str):
        """
        Run the data ingestion pipeline for a single file.
        
        Args:
            file_name: Name of the CSV file to be ingested.
            table_name: Name of the table in the database.
        """
        try:
            dataframe = self.read_csv_file(file_name)
            self.write_to_database(dataframe, table_name)
        except Exception as e:
            raise ValueError(f"Error in data ingestion pipeline: {str(e)}")

    def save_ingested_data(self, file_name: str, output_file: str):
        """
        Save the ingested data to a CSV file.
        
        Args:
            file_name: Name of the CSV file to be ingested.
            output_file: Path to save the ingested data as a CSV file.
        """
        try:
            ingested_data = self.read_csv_file(file_name)
            ingested_data.to_csv(output_file, index=False)
            print(f"Ingested data saved to: {output_file}")
        except Exception as e:
            raise ValueError(f"Error saving ingested data: {str(e)}")

if __name__ == "__main__":
    data_path = "data/raw"
    db_connection_string = "sqlite:///data/processed/fraud_data.db"  # Update with your database connection string
    
    input_file = "synthetic_fraud_data.csv"
    table_name = "fraud_data"
    
    data_ingestion = DataIngestion(data_path, db_connection_string)
    data_ingestion.run_ingestion_pipeline(input_file, table_name)
    
    output_file = "data/processed/ingested_data.csv"
    data_ingestion.save_ingested_data(input_file, output_file)
