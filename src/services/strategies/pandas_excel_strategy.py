import pandas as pd
import logging


def _make_column_names_unique(columns):
    seen = {}
    unique_columns = []
    for col in columns:
        if col not in seen:
            seen[col] = 0
            unique_columns.append(col)
        else:
            seen[col] += 1
            unique_columns.append(f"{col}.{seen[col]}")
    return unique_columns


class PandasExcelStrategy:
    def process(self, file_path: str) -> dict[str, pd.DataFrame]:
        """
        Load an Excel (.xls, .xlsx, .xlsm, .xlsb, .odf, .ods, .odt) file.

        Args:
            file_path (str): The path to the Excel file.

        Returns:
            dict[str, pd.DataFrame]: A dictionary containing a key (sheet_name)
                and value (the table as a pd.DataFrame), since a spreadsheet has multiple tables.
        """

        processed_sheets: dict[str, pd.DataFrame] = {}
        try:
            all_sheets: dict[str, pd.DataFrame] = pd.read_excel(
                file_path, sheet_name=None, header=None
            )

            for sheet_name, df in all_sheets.items():
                if not df.iloc[0].apply(lambda x: isinstance(x, str)).all():
                    # No valid header; set default column names
                    df.columns = [f"col_{i}" for i in range(df.shape[1])]
                else:
                    # Valid header: Use the first row as header
                    df.columns = df.iloc[0]

                processed_sheets[sheet_name] = df

            for sheet_name, df in all_sheets.items():
                # Make column names unique if necessary
                df.columns = _make_column_names_unique(df.columns)
                df = df[1:].reset_index(drop=True)
                processed_sheets[sheet_name] = df

        except Exception as e:
            logging.error(f"Cannot read file '{file_path}'. Error: {str(e)}")

        return processed_sheets
