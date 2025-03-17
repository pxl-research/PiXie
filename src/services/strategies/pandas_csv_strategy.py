import pandas as pd
import csv
import logging


class PandasCSVStrategy:
    def process(self, file_path: str) -> pd.DataFrame:
        """
        Load a CSV (.csv) file.

        Args:
            file_path (str): The path to the .csv file.

        Returns:
            pd.DataFrame: Pandas DataFrame containing the content of the CSV file.
        """

        def _detect_csv_delimiter(file_path: str) -> str:
            delimiter = ","
            with open(file_path, "r") as file:
                sample = "\n".join(file.readlines(10))
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            return delimiter

        try:
            delimiter = _detect_csv_delimiter(file_path)

            # Try reading with the default header and
            # check if the first row has valid header-like strings
            df = pd.read_csv(file_path, header="infer", sep=delimiter)
            if not df.columns.to_series().apply(lambda x: isinstance(x, str)).all():
                # Reset to default column names if headers are invalid
                df = pd.read_csv(file_path, header=None, sep=",")
                df.columns = [f"col_{i}" for i in range(df.shape[1])]
        except pd.errors.ParserError:
            # If parsing fails, assume no header
            df = pd.read_csv(file_path, header=None, sep=delimiter)
            df.columns = [f"col_{i}" for i in range(df.shape[1])]
        except Exception as e:
            logging.error(f"Cannot read file '{file_path}'. Error: {str(e)}")

        return df
