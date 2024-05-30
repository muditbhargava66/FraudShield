import os
import pandas as pd
from sqlalchemy import create_engine
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataIngestion:
    def __init__(self, data_path: str, db_connection_string: str):
        self.data_path = data_path
        self.db_connection_string = db_connection_string
        self.engine = create_engine(db_connection_string)

    def read_csv_file(self, file_name: str) -> pd.DataFrame:
        """
        Read a single CSV file and return a DataFrame.
        
        Args:
            file_name: Name of the CSV file to be read.
        
        Returns:
            DataFrame containing data from the CSV file.
        """
        file_path = os.path.join(self.data_path, file_name)
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Successfully read file: {file_path}")
            return df
        except pd.errors.EmptyDataError:
            logger.error(f"Empty data file: {file_path}")
            raise ValueError(f"Empty data file: {file_path}")
        except pd.errors.ParserError:
            logger.error(f"Invalid data format in file: {file_path}")
            raise ValueError(f"Invalid data format in file: {file_path}")

    def write_to_database(self, dataframe: pd.DataFrame, table_name: str):
        """
        Write the DataFrame to the specified database table.
        
        Args:
            dataframe: DataFrame to be written to the database.
            table_name: Name of the table in the database.
        """
        conn = None
        try:
            conn = self.engine.connect()
            dataframe.to_sql(table_name, con=conn, if_exists='replace', index=False)
            logger.info(f"Data ingested successfully into table: {table_name}")
        except Exception as e:
            logger.error(f"Error writing to database: {str(e)}")
            raise ValueError(f"Error writing to database: {str(e)}")
        finally:
            if conn is not None:
                conn.close()

    def run_ingestion_pipeline(self, file_name: str, table_name: str):
        """
        Run the data ingestion pipeline for a single file.
        
        Args:
            file_name: Name of the CSV file to be ingested.
            table_name: Name of the table in the database.
        """
        try:
            logger.info(f"Starting data ingestion pipeline for file: {file_name}")
            dataframe = self.read_csv_file(file_name)
            self.write_to_database(dataframe, table_name)
            logger.info(f"Data ingestion pipeline completed successfully for file: {file_name}")
        except Exception as e:
            logger.error(f"Error in data ingestion pipeline: {str(e)}")
            raise ValueError(f"Error in data ingestion pipeline: {str(e)}")

    def save_ingested_data(self, file_name: str, output_file: str):
        """
        Save the ingested data to a CSV file.
        
        Args:
            file_name: Name of the CSV file to be ingested.
            output_file: Path to save the ingested data as a CSV file.
        """
        try:
            logger.info(f"Saving ingested data from file: {file_name} to output file: {output_file}")
            ingested_data = self.read_csv_file(file_name)
            ingested_data.to_csv(output_file, index=False)
            logger.info(f"Ingested data saved successfully to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving ingested data: {str(e)}")
            raise ValueError(f"Error saving ingested data: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Data Ingestion Pipeline')
    parser.add_argument('--data_path', type=str, default='data/raw', help='Path to the raw data directory')
    parser.add_argument('--db_connection_string', type=str, default='sqlite:///data/processed/fraud_data.db', help='Database connection string')
    parser.add_argument('--input_file', type=str, default='synthetic_fraud_data.csv', help='Name of the input CSV file')
    parser.add_argument('--table_name', type=str, default='fraud_data', help='Name of the database table')
    parser.add_argument('--output_file', type=str, default='data/processed/ingested_data.csv', help='Path to save the ingested data')
    
    args = parser.parse_args()
    
    data_ingestion = DataIngestion(args.data_path, args.db_connection_string)
    data_ingestion.run_ingestion_pipeline(args.input_file, args.table_name)
    data_ingestion.save_ingested_data(args.input_file, args.output_file)