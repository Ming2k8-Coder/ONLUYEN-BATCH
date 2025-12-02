import json
import re
import sys
import time
from typing import Dict, Any, List, Union
# Import the function from the provided submodule
from sub_module.TIMESTAMPGen import generate_timestamp_sequence # Assuming this is the correct function name



# IMPORTANT: Replace these with the actual file names if they change.
ANSWER_FILE = "Nguyễn Tuấn Minh-6925175257021d562da69e90-ANSWER.json"
QUESTION_FILE = "assignment_response.json"

def debug_print(message: str, debug_mode: bool):
    """Helper function to print messages only if debug_mode is True."""
    if debug_mode:
        print(f"[DEBUG] {message}")

def clean_content(html_string: str) -> str:
    """
    Strips HTML tags (like <p>, <strong>, <span>) and excessive whitespace
    from the content string for reliable comparison.
    """
    # 1. Strip all HTML/XML tags
    text = re.sub(r'<[^>]*>', '', html_string)
    # 2. Strip leading/trailing whitespace
    text = text.strip()
    # 3. Strip common ending punctuation (. or ,) if it's outside math markup
    text = text.strip('.')
    text = text.strip(',')
    return text

def solve_assignment(answer_data_str: str, question_data_str: str, debug_mode: bool = False) -> Dict[str, Union[List[Dict[str, Any]], str, int]]:
    """
    Parses two JSON strings, matches correct answers to question options, 
    generates timestamps, and constructs the submission payload 
    dictionary in the format required by the 'submit_assignment' endpoint.

    The returned dictionary contains:
    - 'listAnswer': A list of matched answers ready for submission.
    - 'preSignedUrlAnswer': The extracted pre-signed URL for the submission PUT request.
    - 'timeServer': The server time extracted from the question data.

    Args:
        answer_data_str (str): JSON string containing the correct answers (as produced by json.dumps).
        question_data_str (str): JSON string containing the questions and options 
                                 (as produced by json.dumps).
        debug_mode (bool, optional): If True, prints detailed debug information. Defaults to False.
        
    Returns:
        Dict[str, Union[List[Dict[str, Any]], str, int]]: The submission payload dictionary.
    """
    debug_print(f"Debug mode is {'ON' if debug_mode else 'OFF'}.", debug_mode)
    
    # 1. Load the data from the two sources
    try:
        answer_data = json.loads(answer_data_str)
        question_data = json.loads(question_data_str)

    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON. Check integrity of input strings.")
        print(f"Details: {e}")
        return {"listAnswer": [], "preSignedUrlAnswer": "ERROR", "timeServer": "ERROR"}
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        return {"listAnswer": [], "preSignedUrlAnswer": "ERROR", "timeServer": "ERROR"}

    # EXTRACT TOP-LEVEL METADATA
    top_level_data = question_data.get('data', {})
    pre_signed_url = top_level_data.get('preSignedUrlAnswer', 'N/A')
    time_server = top_level_data.get('timeServer', 'N/A')
    
    print("--- Assignment Metadata ---")
    print(f"Time Server: {time_server}")
    print(f"Pre-Signed Answer URL: {pre_signed_url}")
    print("---------------------------")
    
    # Determine the starting timestamp for answer updates
    try:
        start_timestamp = int(time_server)
    except (ValueError, TypeError):
        start_timestamp = int(time.time())
        print(f"Warning: timeServer '{time_server}' is invalid. Using current time {start_timestamp} as start.")


    # 2. Build a map of Question ID -> Correct Answer Data (including type)
    answer_map = {}
    try:
        for item in answer_data.get('data', []):
            question_id = item.get('numberQuestion')
            type_answer = item.get('typeAnswer') # <-- Lấy typeAnswer
            content_list = item.get('content') # content_list là list, có thể chứa 1 phần tử (type 0, 5) hoặc nhiều phần tử (type 1)
            
            # Chỉ xử lý nếu có QID và content_list không rỗng
            if question_id is not None and content_list is not None:
                
                # Đối với type 0, 5: raw_answer là phần tử đầu tiên, cleaned_answer cũng được tạo từ nó
                raw_answer = content_list[0] if content_list and type_answer != 1 else ''
                cleaned_answer = clean_content(raw_answer)
                
                # Store Question ID -> Answer Data mapping
                answer_map[question_id] = {
                    'content': content_list,        # Danh sách nội dung (có thể là [raw_content] hoặc ["true", "false",...])
                    'cleaned_content': cleaned_answer, # Cleaned content (chỉ dùng cho type 0)
                    'type': type_answer
                }
                debug_print(f"Mapped QID {question_id} (Type {type_answer}): Content={content_list}", debug_mode)
    except Exception as e:
        print(f"Error processing answer data structure: {e}")
        return {"listAnswer": [], "preSignedUrlAnswer": pre_signed_url, "timeServer": time_server}

    if not answer_map:
        print("Error: Could not extract any question answers from the answer data.")
        return {"listAnswer": [], "preSignedUrlAnswer": pre_signed_url, "timeServer": time_server}

    debug_print(f"Full Answer Map: {answer_map}", debug_mode)
    print(f"Successfully loaded {len(answer_map)} correct answers.")
    print("-------------------------------------------------------")
    print("Results: Question ID -> Chosen Option Key (idOption) or Text Answer")
    print("-------------------------------------------------------")

    # 3. Process the Question Data and match answers
    submission_answers: List[Dict[str, Any]] = []
    
    question_list = top_level_data.get('data', [])
    num_questions = len(question_list)

    # Generate timestamps for all potential answers
    timestamp_sequence = generate_timestamp_sequence(
        start=start_timestamp + 10,  
        step=5,           
        random_range=2,   
        count=num_questions
    )
    ts_iter = iter(timestamp_sequence)

    for item in question_list:
        data_standard = item.get('dataStandard') 
        
        # Xử lý dataMaterial nếu dataStandard không có
        if data_standard is None:
            data_material = item.get('dataMaterial', {})
            data_content = data_material.get('data') 
            
            if isinstance(data_content, list) and data_content:
                data_standard = data_content[0]
            else:
                data_standard = {} 
        
        if data_standard is None:
            data_standard = {}
            
        question_id = data_standard.get('numberQuestion') 
        step_id = data_standard.get('stepId') 
        
        if question_id is None:
            debug_print(f"Skipping item: 'numberQuestion' (ID) is missing.", debug_mode)
            continue

        # Lấy dữ liệu đáp án từ map đã tạo
        correct_answer_data = answer_map.get(question_id)

        if correct_answer_data is None:
            print(f"Warning: No answer found for Question ID {question_id}. Skipping.")
            continue
        
        type_answer = correct_answer_data.get('type')
        correct_answer_content_cleaned = correct_answer_data.get('cleaned_content')
        correct_answer_content_list = correct_answer_data.get('content')
        
        # Biến để lưu nội dung sẽ gửi đi trong trường submission (ID hoặc Text/List of Texts)
        submission_content: List[str] = []
        # Biến để lưu tên khóa (optionId hoặc optionText)
        submission_key: str = 'optionText' 
        match_found = False
        
        # --- LOGIC DỰA TRÊN typeAnswer ---

        if type_answer == 0:
            # Type 0: Multiple Choice / Select Answer
            debug_print(f"\n--- Processing QID {question_id} (Type 0) ---", debug_mode)
            debug_print(f"Target Cleaned Answer: '{correct_answer_content_cleaned}'", debug_mode)

            options = data_standard.get('options', [])
            for option in options:
                option_key = option.get('idOption') 
                raw_option_content = option.get('content')
                
                if raw_option_content and option_key is not None:
                    cleaned_option_content = clean_content(raw_option_content)
                    
                    debug_print(f"  Comparing Option {option_key}: Cleaned='{cleaned_option_content}'", debug_mode)
                    
                    if cleaned_option_content == correct_answer_content_cleaned:
                        print(f"Question {question_id} (Step ID: {step_id}): Option {option_key} (Match: '{correct_answer_content_cleaned}')")
                        
                        # Dùng idOption làm nội dung
                        submission_content.append(str(option_key)) 
                        # SỬ DỤNG KHÓA optionId
                        submission_key = 'optionId'
                        match_found = True
                        break

        elif type_answer == 1:
            # Type 1: Multiple Select (Chọn nhiều đáp án hoặc Đúng/Sai) - THEO YÊU CẦU MỚI
            debug_print(f"\n--- Processing QID {question_id} (Type 1) ---", debug_mode)
            print(f"Question {question_id} (Step ID: {step_id}): Submission is list of true/false strings (type 1).")
            
            # Sử dụng danh sách nội dung đáp án thô (giả định đã là ["true", "false", ...])
            if correct_answer_content_list:
                submission_content = correct_answer_content_list
                # Giữ khóa optionText
                submission_key = 'optionText'
                match_found = True
            else:
                print(f"Warning: Type 1 for QID {question_id} has empty content list. Skipping.")

        elif type_answer == 5:
            # Type 5: Fill-in-the-Blank / Short Answer
            debug_print(f"\n--- Processing QID {question_id} (Type 5) ---", debug_mode)
            print(f"Question {question_id} (Step ID: {step_id}): Submission is direct answer text (type 5).")
            
            # Sử dụng nội dung đáp án thô trực tiếp (phần tử đầu tiên)
            if correct_answer_content_list:
                submission_content.append(correct_answer_content_list[0])
                # Giữ khóa optionText
                submission_key = 'optionText'
                match_found = True
            else:
                print(f"Warning: Type 5 for QID {question_id} has empty content list. Skipping.")

        else:
            # Xử lý các loại typeAnswer khác hoặc không có
            print(f"Question {question_id} (Step ID: {step_id}): Unsupported or unmatched type ({type_answer}). Skipping.")
            continue
        
        # Chỉ tạo payload nếu tìm thấy đáp án
        if match_found and submission_content is not None: # Dùng is not None vì submission_content có thể là list rỗng
            # Get the next timestamp
            current_timestamp = next(ts_iter, int(time.time()))

            # Dynamically create the dictionary item based on the submission key
            submission_answers.append({
                submission_key: submission_content, # Uses 'optionId' (list of IDs) or 'optionText' (list of strings/values)
                'id': step_id, 
                'isSkip': False,
                'studentDoRight': None,
                'timeUpdate': current_timestamp
            })

        # Cảnh báo nếu type 0 không tìm thấy đáp án khớp
        if type_answer == 0 and not match_found:
            print(f"Question {question_id} (Step ID: {step_id}): No matching option found! Expected: '{correct_answer_content_cleaned}'")
            
    print("-------------------------------------------------------")
    print("Processing complete.")
    
    # 4. Return the final payload structure
    final_payload = {
        'listAnswer': submission_answers,
        'preSignedUrlAnswer': pre_signed_url,
        'timeServer': time_server
    }
    
    debug_print(f"\nFinal Submission Payload Structure: {json.dumps(final_payload, indent=2)}", debug_mode)
    
    return final_payload

if __name__ == "__main__":
    # Command-line entry point now reads both the answer and question files 
    # into strings before passing them to the solve_assignment function.
    is_debug = '--debug' in sys.argv
    try:
        # Read the answer file content into a string
        with open(ANSWER_FILE, 'r', encoding='utf-8') as f:
            answer_data_string = f.read()
            
        # Read the question file content into a string
        with open(QUESTION_FILE, 'r', encoding='utf-8') as f:
            question_data_string = f.read()
            
        # Call solve_assignment with both contents as strings
        result_payload = solve_assignment(answer_data_string, question_data_string, debug_mode=is_debug)
        
        if result_payload and result_payload.get('listAnswer'):
            print("\n--- Summary of Prepared Answers (Submission Format) ---")
            print(json.dumps(result_payload['listAnswer'], indent=2))
        elif result_payload:
            print("\n--- No answers were matched successfully. ---")
            
    except FileNotFoundError as e:
        print(f"Error: Could not find required file: {e.filename} to run standalone.")
    except Exception as e:
        print(f"An unexpected error occurred during standalone execution: {e}")