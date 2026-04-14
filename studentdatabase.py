import csv
import io
from typing import Optional, Tuple, Dict, List

class StudentDatabase:
    def __init__(self, csv_filepath: str):
        self.csv_filepath = csv_filepath
        self.students: Dict[int, dict] = {} # Map STT -> Student Data
        self.last_stt: int = 0
        self._load_data()

    def _load_data(self):
        """Loads the CSV data into memory once."""
        try:
            with open(self.csv_filepath, 'r', encoding='utf-8') as f:
                csv_string = f.read()
        except FileNotFoundError:
            print(f"Error: File not found at {self.csv_filepath}")
            return

        lines = csv_string.strip().split('\n')
        if not lines:
            return

        # Fix header issue if present
        if ',isWrongPass' in lines[0]:
            lines[0] = lines[0].replace(',isWrongPass', ';isWrongPass')
        
        # Determine delimiter - Assuming ';' based on previous code, but good to be safer
        # or just stick to what worked: ';'
        reader = csv.DictReader(io.StringIO('\n'.join(lines)), delimiter=';')
        
        # Sanitize headers
        if reader.fieldnames:
             reader.fieldnames = [h.lstrip('\ufeff').strip() for h in reader.fieldnames]

        for row in reader:
            try:
                stt = int(row.get('STT', 0))
                if stt > 0:
                    self.students[stt] = row
                    if stt > self.last_stt:
                        self.last_stt = stt
            except ValueError:
                continue

    def get_last_stt(self) -> int:
        return self.last_stt

    def get_credentials(self, stt_count: int, debug: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        student = self.students.get(stt_count)
        if not student:
            if debug:
                 print(f"STT {stt_count} not found in loaded data.")
            return (None, None, None)

        student_name = student.get('Họ và tên', '').strip()
        username = student.get('Tài khoản', '').strip()
        password = student.get('Mật khẩu', '').strip()
        
        # Check isWrongPass
        is_wrong_pass = student.get('isWrongPass', 'FALSE').strip().upper()
        
        if is_wrong_pass == 'TRUE':
            if debug:
                print(f"STT {stt_count}: Account marked as having the wrong password.")
            return (None, None, None)
        
        if debug:
            print(f"STT {stt_count}: Valid account found.")
        return (student_name, username, password)

# For backward compatibility if needed, or primarily for singleton usage
# But better to instantiate in main execution.
if __name__ == "__main__":
    db = StudentDatabase('Acc-onluyen.csv')
    print(f"Last STT: {db.get_last_stt()}")
    print(f"STT 1: {db.get_credentials(1)}")