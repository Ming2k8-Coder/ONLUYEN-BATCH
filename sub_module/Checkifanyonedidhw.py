from studentdatabase import *
from sub_module.POSTLogin import *
from sub_module.GETHWListAll import *
from sub_module.GETHWQuestDoing import *
from typing import Optional, List, Tuple, Dict, Any

debug = False

# --- UPDATED UTILITY FUNCTION ---
def find_full_logid(all_assignments: List[Dict[str, Any]], partial_logid: str) -> Optional[str]:
    """
    Searches the list of assignments for a logid that contains the partial_logid as a substring.
    
    Args:
        all_assignments: The detailed list of homework assignments.
        partial_logid: The partial log ID (e.g., '3107f9').
        
    Returns:
        The full log ID if found, otherwise None.
    """
    # Normalize the partial log ID for case-insensitive comparison
    normalized_partial = partial_logid.lower()
    
    for assignment in all_assignments:
        log_id = assignment.get('logid')
        if log_id and normalized_partial in log_id.lower():
            # Found a match where partial_logid is a substring of the full log_id
            return log_id
    
    return None
# -----------------------------

# New return type: Tuple[str, List[Tuple[str, str]], List[Tuple[str, Optional[str]]]]
# (full_logid, [(name_done, token_done), ...], [(name_not_done, token_not_done_or_none), ...])
def check_if_anyone_did_hw(FILE_PATH, partial_logid, debug: bool = False) -> Tuple[str, List[Tuple[str, str]], List[Tuple[str, Optional[str]]]]:
    students_done_with_tokens: List[Tuple[str, str]] = []
    students_not_done_with_tokens: List[Tuple[str, Optional[str]]] = []
    
    full_logid: Optional[str] = None
    
    laststudent = get_last_stt(FILE_PATH)
    if laststudent is None:
        print("Could not determine the last student STT. Returning empty lists.")
        return (partial_logid, [], [])

    for stt in range(1, laststudent + 1):
        if debug:
            print('-'*5 + f" Checking STT {stt} " + '-'*5)
        name, username, password = get_credentials(FILE_PATH, stt, debug=debug)
        
        current_token: Optional[str] = None
        
        if name is None or username is None or password is None:
            if debug:
                print(f"STT {stt}: Skipping due to invalid account or not found.\n")
            continue

        if debug:
            print(f"STT {stt}: Attempting login for user '{username}'...")
        
        # 1. Attempt Login
        response = make_login_request(username, password, debug=debug)
        if response is None:
            print(f"STT {stt}: Login failed for user '{username}'. Cannot get access token.\n")
            students_not_done_with_tokens.append((name, None))
            continue

        current_token = response['access_token']
        
        if debug:
            print(f"STT {stt}: Login successful. Fetching homework list...")
        
        # 2. Fetch HW List
        hw_list = fetch_mission_data(current_token) # type: ignore
        if hw_list is None:
            print(f"STT {stt}: Failed to fetch homework list. Cannot confirm status.\n")
            students_not_done_with_tokens.append((name, current_token))
            continue

        # 3. Check Homework Status and find full logid
        is_done = False
        if hw_list and hw_list.get('success') is True and isinstance(hw_list.get('data'), list):
            
            all_assignments = extract_detailed_summary(hw_list)
            
            # --- CRITICAL LOGIC: Find the full log ID on the first successful fetch ---
            if full_logid is None:
                found_id = find_full_logid(all_assignments, partial_logid)
                if found_id:
                    full_logid = found_id
                    print(f"FULL LOG ID found: {full_logid}. Using this ID for all subsequent checks.")
                else:
                    # If the full ID cannot be found, we cannot check this student for this HW.
                    print(f"WARNING: Could not find full log ID matching '{partial_logid}'. Skipping student check for this HW.")
                    students_not_done_with_tokens.append((name, current_token))
                    continue # Skip current student if we can't confirm the HW ID.
            # -------------------------------------------------------------------------
            
            # Use the determined full_logid for the check
            logid_to_check = full_logid
            target_status = "Done"
            
            if check_assignment_availability(all_assignments, logid_to_check, target_status):
                if debug:
                    print(f"STT {stt}: '{name}' DONE the homework.")
                students_done_with_tokens.append((name, current_token)) # type: ignore
                is_done = True
            
        # 4. Append to "not done" list if the homework was NOT done
        if not is_done:
            if debug:
                print(f"STT {stt}: '{name}' DID NOT DO the homework or status could not be confirmed as 'Done'.")
            students_not_done_with_tokens.append((name, current_token))

    print('-'*10 + " CHECK COMPLETE " + '-'*10)
    
    # Return the full log ID (or partial if not found) and the two lists
    final_logid = full_logid if full_logid else partial_logid
    return (final_logid, students_done_with_tokens, students_not_done_with_tokens)

if __name__ == "__main__":
    
    FILE_PATH = 'Acc-onluyen copy.csv'
    # Use an internal substring for testing this feature
    LOGID = "dc126f"  # Example partial homework log ID

    print(f"--- TESTING check_if_anyone_did_hw with file path: {FILE_PATH} and partial logid: {LOGID} ---")
    
    # Unpack the three return values
    final_logid, students_done_results, students_not_done_results = check_if_anyone_did_hw(FILE_PATH, LOGID)

    print("\n--- FINAL RESULTS ---")
    print(f"The FULL LOG ID used for checking was: **{final_logid}**\n")
    
    print("## Students Who Done Homework ✅ (Name, Token)")
    if students_done_results:
        for name, token in students_done_results:
            print(f"Name: {name}, Access Token (JWT): {token[:10]}...") 
    else:
        print("None")
        
    print("\n## Students Who Did Not Do Homework ❌ (Name, Token or None)")
    if students_not_done_results:
        for name, token in students_not_done_results:
            token_display = f"{token[:10]}..." if token else "**LOGIN FAILED**"
            print(f"Name: {name}, Access Token (JWT): {token_display}")
    else:
        print("All checked students completed it.")