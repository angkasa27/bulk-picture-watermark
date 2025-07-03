import pandas as pd  # Import pandas for handling Excel and CSV files
import os  # Optional: for file path checks

def excel_sheet_to_csv(excel_file_path: str, sheet_name: str, csv_output_path: str):
    """
    Reads a specific sheet from an Excel file and saves it as a CSV.

    :param excel_file_path: Path to the source Excel (.xlsx or .xls) file
    :param sheet_name: Name of the sheet to extract
    :param csv_output_path: Path where the CSV file will be saved
    """
    
    # Validate the Excel file path exists
    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
    
    # Load the Excel file and read the specific sheet into a DataFrame
    try:
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
    except ValueError as e:
        raise ValueError(f"Could not find the sheet '{sheet_name}' in the file.") from e
    
    # Save the DataFrame to CSV
    df.to_csv(csv_output_path, index=False)  # index=False to avoid saving row numbers
    
    print(f"✅ Sheet '{sheet_name}' has been successfully saved to '{csv_output_path}'.")


# Example usage:
if __name__ == "__main__":
    excel_path = "Data ATP_Rev.xlsx"             # Input Excel file
    sheet = "Inside view"                 # Sheet name to extract
    csv_path = "Inside view.csv"   # Output CSV file name

    excel_sheet_to_csv(excel_path, sheet, csv_path)