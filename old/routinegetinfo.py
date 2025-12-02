from POSTLogin import *
from GETHWSpecific import *
from GETHWList import *

username = "minhnt65@c3ltk.hanam.edu.vn"
userpass = "779862"

def main(username, userpassword, debug: bool = False):
    login_json = make_login_request({
        "phoneNumber": username,
        "password": userpassword,
        "rememberMe": True,
        "userName": username,
        "socialType": "Email"
    }, debug=debug)
    if login_json and 'access_token' in login_json:
        token = login_json['access_token']
        print("\n*** Login successful, proceeding to fetch assignment list ***\n")
        
        assignment_list = fetch_assignments(token, debug=debug)
        if assignment_list and 'data' in assignment_list:
            assignments = assignment_list['data']
            print(f"\n*** Found {len(assignments)} assignments. Fetching details for each... ***\n")
            
            for assignment in assignments:
                assign_id = assignment.get('id')
                if assign_id:
                    fetch_data_and_parse(assign_id, token, write_to_file=False, debug=debug)
                else:
                    print("-> Assignment ID not found, skipping...")
        else:
            print("-> Failed to retrieve assignment list or no data found.")
    else:
        print("-> Login failed, cannot proceed to fetch assignments.")

main(username,userpass, debug=True)