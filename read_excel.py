import pandas as pd
import sys

file_path = sys.argv[1]
try:
    xl = pd.ExcelFile(file_path)
    for sheet in xl.sheet_names:
        if '5A' in sheet.upper():
            print("Processing sheet:", sheet)
            
            df_temp = pd.read_excel(file_path, sheet_name=sheet, nrows=30, header=None)
            header_row_index = -1
            for idx, row in df_temp.iterrows():
                row_str = ' '.join(str(val).upper() for val in row.values if pd.notna(val))
                if 'LAST NAME' in row_str or 'FIRST NAME' in row_str:
                    header_row_index = idx
                    break
            
            if header_row_index != -1:
                print(f"Found header at row {header_row_index}")
                df = pd.read_excel(file_path, sheet_name=sheet, skiprows=header_row_index)
                print("Columns:", df.columns.tolist()[:20])
                print("Data sample:")
                for i in range(min(3, len(df))):
                    # Only print non-null values to save space
                    row_dict = {k: v for k, v in df.iloc[i].to_dict().items() if pd.notna(v) and 'Unnamed' not in str(k) or pd.notna(v)}
                    # Let's just print a simplified version
                    print({k: v for k, v in row_dict.items() if 'Unnamed' not in str(k)})
            else:
                print("Could not find table header.")
            break
except Exception as e:
    print("Error:", e)
