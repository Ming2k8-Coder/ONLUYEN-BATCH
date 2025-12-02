import csv
from io import StringIO
from typing import Optional, Tuple


def _load_csv_string_and_reader(csv_filepath: str):
    """Internal utility to load CSV content and prepare the reader."""
    # --- SIMULATION START ---
    # In a real Python environment, this block would handle file reading:
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as f:
            csv_string = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {csv_filepath}")
        return None, None
    # --- SIMULATION END ---
    
    lines = csv_string.strip().split('\n')
    if lines and ',isWrongPass' in lines[0]:
        lines[0] = lines[0].replace(',isWrongPass', ';isWrongPass')
        
    csvfile = StringIO('\n'.join(lines))
    reader = csv.reader(csvfile, delimiter=';')
    
    return csv_string, reader

def get_last_stt(csv_filepath: str) -> Optional[int]:
    """
    Finds and returns the largest sequential number (STT) in the CSV data.

    Args:
        csv_filepath: The path to the CSV file (e.g., 'Acc-onluyen.csv').

    Returns:
        The highest STT as an integer, or None if the file is empty or STT column is missing.
    """
    _, reader = _load_csv_string_and_reader(csv_filepath)
    if not reader:
        return None
        
    try:
        header = next(reader)
    except StopIteration:
        print("Error: CSV string has no header.")
        return None

    # Clean up the header names (remove BOM and strip whitespace)
    header = [h.lstrip('\ufeff').strip() for h in header]

    try:
        stt_idx = header.index('STT')
    except ValueError:
        print("Error: Missing required 'STT' column in CSV.")
        return None
    
    max_stt = 0
    
    # Iterate through the data rows
    for row in reader:
        if not row or len(row) <= stt_idx:
            continue
            
        try:
            current_stt = int(row[stt_idx].strip())
            if current_stt > max_stt:
                max_stt = current_stt
        except ValueError:
            # Skip rows where the STT value is not a number
            continue
            
    return max_stt if max_stt > 0 else None

def get_credentials(csv_filepath: str, stt_count: int, debug: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts the name (Họ và tên), username (Tài khoản), and password (Mật khẩu) 
    from the CSV file specified by csv_filepath, based on the sequential number (STT).

    The function returns (Name, Username, Password) if 'isWrongPass' is 'False' or omitted.
    If 'isWrongPass' is 'True', the function returns (None, None, None).

    Args:
        csv_filepath: The path to the CSV file (e.g., 'Acc-onluyen.csv').
                      NOTE: In a real environment, this function would open and read the file.
        stt_count: The sequential number (STT) of the student to search for.

    Returns:
        A tuple (Name, Username, Password), or (None, None, None) if 'isWrongPass' is 'True'
        or the STT is not found.
    """
    csv_string, reader = _load_csv_string_and_reader(csv_filepath)
    if not reader:
        return (None, None, None)

    # Read the column headers
    try:
        header = next(reader)
    except StopIteration:
        print("Error: CSV string has no header.")
        return (None, None, None)

    # Clean up the header names to remove potential Byte Order Mark (\ufeff)
    header = [h.lstrip('\ufeff').strip() for h in header]

    # Determine the indices of the required columns
    try:
        stt_idx = header.index('STT')
        name_idx = header.index('Họ và tên')
        taikhoan_idx = header.index('Tài khoản')
        matkhau_idx = header.index('Mật khẩu')
        
        # isWrongPass might be missing
        iswrongpass_idx = header.index('isWrongPass') if 'isWrongPass' in header else -1
        
    except ValueError as e:
        print(f"Error: Missing required column in CSV: {e}")
        return (None, None, None)

    # Iterate through the data rows
    for row in reader:
        # Check for sufficient columns
        required_indices = [stt_idx, name_idx, taikhoan_idx, matkhau_idx]
        if iswrongpass_idx != -1:
            required_indices.append(iswrongpass_idx)
            
        if not row or len(row) <= max(required_indices):
            continue

        # Check if STT matches
        try:
            if int(row[stt_idx]) == stt_count:
                # Student found
                student_name = row[name_idx].strip()
                username = row[taikhoan_idx].strip()
                password = row[matkhau_idx].strip()
                
                # --- START Check isWrongPass Logic ---
                is_wrong_pass = 'FALSE' # Default assumption: valid account
                
                # Check for the column index and if the row actually has a value at that index
                if iswrongpass_idx != -1 and len(row) > iswrongpass_idx:
                    # Check the actual value in the column
                    cell_value = row[iswrongpass_idx].strip().upper()
                    if cell_value == 'TRUE':
                        is_wrong_pass = 'TRUE'
                
                # Check the isWrongPass condition
                if is_wrong_pass == 'TRUE':
                    if debug:
                        print(f"STT {stt_count}: Account marked as having the wrong password. Returning None for all fields.")
                    return (None, None, None) 
                else:
                    if debug:
                        print(f"STT {stt_count}: Valid account. Returning name, username, and password.")
                    return (student_name, username, password) 

        except ValueError:
            # Skip rows where the STT value is not a number
            continue
    
    # If the loop finishes without finding the STT
    print(f"STT {stt_count} not found in the data.")
    return (None, None, None) 

if __name__ == "__main__":
    # Define the file path for the simulation
    FILE_PATH = 'Acc-onluyen.csv'

    print(f"--- TESTING with file path: {FILE_PATH} ---")
    
    # --- NEW: Test get_last_stt function ---
    last_stt = get_last_stt(FILE_PATH)
    print(f"The last STT found in the file is: {last_stt}\n")

    print("--- TESTING get_credentials ---")

    print("--- STT 1 (isWrongPass = False) ---")
    # STT 1: Valid
    result1 = get_credentials(FILE_PATH, 1)
    print(f"Result for STT 1: {result1}\n")

    print("--- STT 2 (isWrongPass = True) ---")
    # STT 2: Wrong password
    result2 = get_credentials(FILE_PATH, 2)
    print(f"Result for STT 2: {result2}\n")

    print("--- STT 4 (Empty isWrongPass column, defaults to False) ---")
    # STT 4: Empty isWrongPass value
    result4 = get_credentials(FILE_PATH, 4)
    print(f"Result for STT 4: {result4}\n")

    print("--- MISSING STT (STT 99) ---")
    # STT 99: Not found
    result_missing = get_credentials(FILE_PATH, 99)
    print(f"Result for STT 99: {result_missing}\n")