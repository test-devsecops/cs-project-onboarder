from datetime import datetime
from utility.helper_functions import HelperFunctions

import csv
import os

class Csv:

    @staticmethod
    def read_csv(file_path, column_index=0):
        
        """Reads a CSV file and returns values from the specified column."""
        extracted_data = []
        
        try:
            with open(file_path, mode='r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)  # Store headers if needed
                
                for row in reader:
                    if row and len(row) > column_index:  # Ensure row has enough columns
                        row_value = row[column_index].strip()
                        is_readable = HelperFunctions.is_readable(row_value)

                        if is_readable:
                            extracted_data.append(row_value)  # Extract desired column
                        else:
                            extracted_data.append("UNREADABLE")
                            print(f"Skipping unreadable value: {row_value}")
                            continue
        
        except Exception as e:
            print(f"Error reading CSV file: {e}")
        
        return extracted_data
    
    @staticmethod
    def extract_to_csv(data_list, fieldnames, directory="./csv_files/", filename="data.csv"):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}.csv"

        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)

        with open(filepath, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames)
            writer.writeheader()
            
            for data in data_list:
                writer.writerow({field: data.get(field, "") for field in fieldnames})

        print(f"Filtered Scan Details saved to {filepath}")

    @staticmethod
    def get_latest_csv(directory):
        """Finds the most recent CSV file in the specified directory."""
        try:
            files = [f for f in os.listdir(directory) if f.endswith(".csv")]
            if not files:
                raise FileNotFoundError("No CSV files found in the directory.")

            # Sort files by modified time (latest first)
            latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
            return os.path.join(directory, latest_file)  # Return full path
        except Exception as e:
            print(f"Error finding latest CSV: {e}")
            return None