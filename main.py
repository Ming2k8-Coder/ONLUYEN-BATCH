import sys
from sub_module.Homework_module.Checkifanyonedidhw import *
from sub_module.Homework_module.GETHWSpecificInfo import *
from sub_module.Homework_module.POSTStartHW import *
from sub_module.Homework_module.PUTAnswers import *
from sub_module.Homework_module.convertREFtoANSDOC import *
import json
from solve import *
import time
from config import *
from studentdatabase import StudentDatabase
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import threading
import io
import os
import datetime

class ThreadLocalLogger(object):
    def __init__(self, filename='latest.log'):
        self.terminal = sys.stdout
        self.local = threading.local()
        self.filename = filename
        # Open in append mode initially or write? Plan said rename at end.
        # Let's write to latest.log and rename later.
        self.log_file = open(filename, "w", encoding='utf-8')
        self.lock = threading.RLock()

    def _get_buffer(self):
        if not hasattr(self.local, 'buffer'):
            self.local.buffer = io.StringIO()
        return self.local.buffer

    def write(self, message):
        # Buffered mode is per-thread
        if getattr(self.local, 'buffering', False):
            self._get_buffer().write(message)
        else:
            self.terminal.write(message)
            with self.lock:
                if self.log_file and not self.log_file.closed:
                    self.log_file.write(message)
                    self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        with self.lock:
            if self.log_file and not self.log_file.closed:
                self.log_file.flush()

    def get_and_clear_local_log(self):
        if hasattr(self.local, 'buffer'):
            content = self.local.buffer.getvalue()
            self.local.buffer = io.StringIO()
            return content
        return ""

    def start_buffering(self):
        self.local.buffering = True
        self._get_buffer() # Ensure buffer exists

    def stop_buffering(self):
        self.local.buffering = False

    def print_to_main(self, message):
        """Force print to main terminal and log file."""
        self.terminal.write(message + "\n")
        with self.lock:
            if self.log_file and not self.log_file.closed:
                self.log_file.write(message + "\n")
                self.log_file.flush()

    def close(self):
        self.log_file.close()

class TableFormatter:
    @staticmethod
    def format_student_table(name, total_time, steps):
        width = 120
        header = f"| Student: {name} | Total Time: {total_time:.3f}s"
        header = header.ljust(width - 1) + "|"
        
        sep = "+" + "-" * (width - 2) + "+"
        col_sep = "+-------------------+----------------------+-------------------+-----------------------------------------------------------------+"
        
        lines = [sep, header, col_sep]
        lines.append(f"| {'Step':<17} | {'Status':<20} | {'Time (s)':<17} | {'Debug / Details':<63} |")
        lines.append(col_sep)
        
        for step in steps:
            s_name = step.get('name', '')
            s_status = step.get('status', '')
            s_time = f"{step.get('time', 0):.3f}"
            s_debug = step.get('debug', '')[:63]
            lines.append(f"| {s_name:<17} | {s_status:<20} | {s_time:<17} | {s_debug:<63} |")
            
        lines.append(col_sep)
        return "\n".join(lines)

    @staticmethod
    def format_reference_table(data_str):
        try:
            data = json.loads(data_str)
            info = data.get('data', {}).get('dataDetail', {})
        except:
            return "Error parsing reference data for table."

        width = 76
        sep = "+" + "-" * (width - 2) + "+"
        header = "| REFERENCE STUDENT EXAM DETAILS".ljust(width - 1) + "|"
        
        lines = [sep, header, sep]
        
        def add_row(key, val):
            lines.append(f"| {key:<23} | {str(val):<46} |")

        add_row("Name", info.get("name", "N/A"))
        add_row("Status", info.get("status", "N/A"))
        add_row("Total Questions", info.get("totalQuestion", 0))
        
        # Format timestamps if possible
        def fmt_ts(ts):
            if not ts: return "N/A"
            return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S - %d/%m/%Y")

        add_row("Start Time", fmt_ts(info.get("startTime")))
        add_row("Submit Time", fmt_ts(info.get("submitTime")))
        
        lines.append(sep)
        return "\n".join(lines)

def process_student_task(student, logid, answer_json, debug_mode, logger):
    """
    Process a single student and record metrics.
    """
    name = student[0]
    token = student[1]
    steps = []
    overall_start = time.perf_counter()
    logger.start_buffering()
    
    def run_step(step_name, func, *args):
        s_start = time.perf_counter()
        res = None
        status = "✅ Success"
        debug_info = ""
        try:
            res = func(*args)
            if step_name == "Start Assignment":
                if not res or not res.json().get('success'):
                    msg = res.json().get('message', 'Unknown Error') if res else "No Response"
                    if msg == "Đang làm bài":
                        status = "✅ Success"
                        debug_info = "Already started"
                    else:
                        status = "❌ Failed"
                        debug_info = msg
                else:
                    debug_info = f"API: {res.status_code} OK"
            elif step_name == "Get Data":
                if not res:
                    status = "❌ Failed"
                else:
                    # Parse JSON safely
                    if isinstance(res, str):
                        obj = json.loads(res)
                    else:
                        obj = res
                    
                    q_count = len(obj.get('data', {}).get('data', []))
                    debug_info = f"Questions: {q_count}"
            elif step_name == "Solve":
                debug_info = f"Payload ready"
            elif step_name == "Submit":
                 # res is (success, status_code, message) from submit_assignment
                 success, code, msg = res if res else (False, 0, "No Response")
                 if not success:
                    status = "❌ Failed"
                    debug_info = msg
                 else:
                    debug_info = f"API: {code} OK"
        except Exception as e:
            status = "❌ Failed"
            debug_info = str(e)
        
        s_end = time.perf_counter()
        steps.append({
            'name': step_name,
            'status': status,
            'time': s_end - s_start,
            'debug': debug_info
        })
        return res, status == "✅ Success"

    # Step Execution
    _, ok = run_step("Start Assignment", start_assignment_request, logid, token, debug_mode)
    exam_data = None
    if ok:
        exam_data, ok = run_step("Get Data", get_assignment_data, token, logid, "debugss")
    
    ready_to_push = None
    if ok:
        datautf = json.dumps(exam_data, indent=4, ensure_ascii=False)
        ready_to_push, ok = run_step("Solve", solve_assignment, answer_json, datautf, debug_mode)
    
    if ok:
        run_step("Submit", submit_assignment, ready_to_push["preSignedUrlAnswer"], ready_to_push["listAnswer"])

    overall_end = time.perf_counter()
    
    # Generate Table
    table = TableFormatter.format_student_table(name, overall_end - overall_start, steps)
    
    # Capture thread local logs
    local_logs = logger.get_and_clear_local_log()
    logger.stop_buffering()
    
    # Final Output - Removed redundant logger.lock to prevent deadlock
    logger.print_to_main(table)
    if debug_mode and local_logs:
        logger.print_to_main("--- TRACE LOGS ---")
        logger.print_to_main(local_logs)
        logger.print_to_main("-" * 20)

def main():
    # Argument Parser
    parser = argparse.ArgumentParser(description="Run the ONLUYEN-BATCH process.")
    parser.add_argument('--debug', '-d', action='store_true', help="Enable debug mode")
    args = parser.parse_args()
    
    # Logger initialization
    logger = ThreadLocalLogger()
    sys.stdout = logger

    # State variables for renaming log file
    assignment_name = "UnknownExam"
    final_logid = "UnknownID"

    try:
        # Initialize Database once
        db = StudentDatabase(CSV_FILE_PATH)

        # 1: GET LOGID
        try:
            logidpartial = input("Please input the logid of the test (partial OK): ")
            print(f"> Input: {logidpartial}")
        except EOFError:
            print("Input stream closed.")
            return

        # 2: Check Login/Status
        # Updated sub-module returns elapsed time
        final_logid, students_done, students_not_done, login_elapsed = check_if_anyone_did_hw(db, logidpartial, args.debug)
        print(f"Total time for getting access tokens: {login_elapsed:.4f} seconds")

        if not students_done:
            print("NO REF STUDENT CAN BE FOUND")
            sys.exit(1)
        if not students_not_done:
            print("ALL STUDENT DID HW")
            sys.exit(0)

        refs_student = students_done[0]
        print(f'REF FOUND: {refs_student[0]}')
        
        # 3: Fetch Reference Data
        rawresp = fetch_data_and_parse(final_logid, refs_student[1], True, args.debug, OUTPUT_JSON_PATTERN.format(student_name=refs_student[0], logid=final_logid))
        
        if rawresp:
            # Print Reference Table
            ref_table = TableFormatter.format_reference_table(rawresp)
            print(ref_table)
            
            # Extract assignment name and FULL logid for filename
            try:
                ref_data = json.loads(rawresp)
                data_obj = ref_data.get('data', {})
                detail_obj = data_obj.get('dataDetail', {})
                
                # Update with FULL values from API
                assignment_name = detail_obj.get('name', assignment_name)
                # Try 'assignId' or 'id' in data_obj - ensure we get the full string
                final_logid = data_obj.get('assignId') or data_obj.get('id') or detail_obj.get('id') or final_logid
                
                # Clean filename strings
                assignment_name = "".join([c for c in assignment_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            except Exception as e:
                print(f"Warning: Could not extract full details for log filename: {e}")

        if rawresp is None:
            raise ValueError("FETCHING ANSWER FAILED")

        answer_json = convert_assignment_json_to_json(rawresp)

        # Save answer file
        answer_filename = ANSWER_FILE_PATTERN.format(student_name=refs_student[0], logid=final_logid)
        with open(answer_filename, 'w', encoding='utf8') as f:
            f.write(str(answer_json))
        
        print('-'*10 + ' ANSWER JSON MADE ' + '-'*10)

        confirm = input("Continue? (Y/N): ")
        print(f"> Confirm: {confirm}")
        if confirm.upper() != "Y":
            sys.exit(0)
            
        start_copy_time = time.perf_counter()
        print(f"Start copying with {DEFAULT_THREAD_COUNT} threads")
        
        # 4: Parallel Processing
        with ThreadPoolExecutor(max_workers=DEFAULT_THREAD_COUNT) as executor:
            # We need STT for the table, but students_not_done doesn't have it.
            # We'll re-match with DB or just use an index. DB stt is better if we can get it.
            # For now, let's just use indices as STT.
            futures = []
            for student in students_not_done:
                futures.append(executor.submit(process_student_task, student, final_logid, answer_json, args.debug, logger))
            
            for future in as_completed(futures):
                future.result()
                
        end_copy_time = time.perf_counter()
        total_proc_time = login_elapsed + (end_copy_time - start_copy_time)
        print("="*40)
        print(f"TOTAL PROCESSING TIME: {total_proc_time:.4f} seconds")
        print("="*40)

    finally:
        logger.close()
        # Rename log file at the end
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_log_name = f"{timestamp}-{assignment_name}-{final_logid}.log"
        try:
            if os.path.exists('latest.log'):
                os.rename('latest.log', new_log_name)
                # We can't print after closing logger easily, so we use print to stderr or just exit
                sys.__stdout__.write(f"\nLog saved to: {new_log_name}\n")
        except Exception as e:
            sys.__stdout__.write(f"\nError renaming log file: {e}\n")

if __name__ == "__main__":
    main()
