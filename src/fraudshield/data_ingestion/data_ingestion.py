"""
FraudShield - Advanced Anomaly Detection Pipeline

This module provides the DataIngestion pipeline class, automating the
extraction of transaction data from CSV sources and secure loading
into standard SQL databases.

File: data_ingestion.py
Author: Mudit Bhargava
License: MIT
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine

# Set up logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/fraudshield_ingest.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class DataIngestion:
    def __init__(self, data_path: str, db_connection_string: str) -> None:
        self.data_path = Path(data_path)
        self.db_connection_string = db_connection_string
        self.engine = create_engine(db_connection_string)

    def read_csv_file(self, file_name: str, **read_csv_kwargs) -> pd.DataFrame:
        """
        Read a single CSV file and return a DataFrame.

        Args:
            file_name: Name of the CSV file to be read.

        Returns:
            DataFrame containing data from the CSV file.
        """
        file_path = self.data_path / file_name

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            df = pd.read_csv(file_path, **read_csv_kwargs)
            logger.info(f"Successfully read file: {file_path}")
            return df
        except pd.errors.EmptyDataError as exc:
            logger.error(f"Empty data file: {file_path}")
            raise ValueError(f"Empty data file: {file_path}") from exc
        except pd.errors.ParserError as e:
            logger.error(f"Invalid data format in file: {file_path} - {e}")
            raise ValueError(f"Invalid data format in file: {file_path}") from e
        except (UnicodeDecodeError, OSError) as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise ValueError(f"Error reading file {file_path}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error reading file {file_path}: {e}")
            raise

    def write_to_database(
        self,
        dataframe: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
        chunksize: Optional[int] = 100,
    ):
        """
        Write the DataFrame to the specified database table.

        Args:
            dataframe: DataFrame to be written to the database.
            table_name: Name of the table in the database.
        """
        if dataframe is None or dataframe.empty:
            logger.warning("Received empty DataFrame. Skipping database write.")
            return
        if not table_name:
            raise ValueError("table_name must be provided.")

        try:
            with self.engine.begin() as conn:
                dataframe.to_sql(
                    table_name,
                    con=conn,
                    if_exists=if_exists,
                    index=False,
                    chunksize=chunksize,
                    # method="multi",
                )
            logger.info(f"Data ingested successfully into table: {table_name}")
        except Exception as e:
            logger.error(f"Error writing to database: {str(e)}")
            raise ValueError(f"Error writing to database: {str(e)}") from e

    def run_ingestion_pipeline(
        self,
        file_name: str,
        table_name: str,
        if_exists: str = "append",
        chunksize: Optional[int] = 10000,
    ) -> None:
        logger.info(f"Starting data ingestion pipeline for file: {file_name}")
        dataframe = self.read_csv_file(file_name)
        self.write_to_database(dataframe, table_name, if_exists=if_exists, chunksize=chunksize)
        logger.info(f"Data ingestion pipeline completed successfully for file: {file_name}")

    def save_ingested_data(self, file_name: str, output_file: str) -> None:
        logger.info(f"Saving ingested data from file: {file_name} to output file: {output_file}")
        ingested_data = self.read_csv_file(file_name)
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ingested_data.to_csv(output_path, index=False)
        logger.info(f"Ingested data saved successfully to: {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Data Ingestion Pipeline")
    parser.add_argument("--data_path", type=str, default="data/raw", help="Path to the raw data directory")
    parser.add_argument(
        "--db_connection_string",
        type=str,
        default="sqlite:///data/processed/fraud_data.db",
        help="Database connection string",
    )
    parser.add_argument("--input_file", type=str, default="synthetic_fraud_data.csv", help="Name of the input CSV file")
    parser.add_argument("--table_name", type=str, default="fraud_data", help="Name of the database table")
    parser.add_argument(
        "--output_file", type=str, default="data/processed/ingested_data.csv", help="Path to save the ingested data"
    )
    parser.add_argument(
        "--if_exists",
        type=str,
        default="append",
        choices=["fail", "replace", "append"],
        help="Behavior if the table already exists",
    )
    parser.add_argument("--chunksize", type=int, default=100, help="Chunk size for database inserts")

    args = parser.parse_args()

    data_ingestion = DataIngestion(args.data_path, args.db_connection_string)
    data_ingestion.run_ingestion_pipeline(
        args.input_file,
        args.table_name,
        if_exists=args.if_exists,
        chunksize=args.chunksize,
    )
    data_ingestion.save_ingested_data(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
