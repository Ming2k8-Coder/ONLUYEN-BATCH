import sys
#sub_modules
from sub_module.Checkifanyonedidhw import *
from sub_module.GETHWSpecificInfo import *
from sub_module.POSTStartHW import *
from sub_module.PUTAnswers import *
from convertREFtoANSDOC import *
import json
from solve import *
import time

debug = False

#START
#1:GET LOGID + CSV (HARDCODED)
FILE_PATH = 'Acc-onluyen.csv'
logidpartial = input("Please input the logid of the test(the scrambled string in searchbar, partial OK):")

#2:check_if_did_hw
logid,students_done, students_not_done = check_if_anyone_did_hw(FILE_PATH, logidpartial, debug)

#3.1:chose 1 student done
if students_done == None or len(students_done) == 0:
    print("NO REF STUDENT CAN BE FOUND")
    sys.exit(1)
if students_not_done == None or len(students_not_done) == 0:
    print("ALL STUDENT DID HW")
    sys.exit(0)
refs_student = students_done[0]

print(f'REF FOUND:{refs_student[0]}')
rawresp=fetch_data_and_parse(logid, refs_student[1],True ,debug, f'{refs_student[0]}-{logid}.json')
print(f"{len(students_done)} student did homework and {len(students_not_done)} didn't")
if rawresp == None:
    raise ValueError("FETCHING ANSWER FAILED")
answer_json = convert_assignment_json_to_json(rawresp)
with open(f'{refs_student[0]}-{logid}-ANSWER.json','w', encoding = 'utf8') as f:
    f.write(str(answer_json))
print('-'*10 + 'ANSWER JSON MADE' + '-'*10)
print("Start copying")
for student in students_not_done:
    start_time = time.perf_counter()
    print('*'*10 + f"Solving for {student[0]}" + '*'*10)
    start_assignment_request(logid,student[1], debug) # type: ignore
    exam_data = get_assignment_data(student[1],logid) # type: ignore
    datautf = json.dumps(exam_data, indent=4, ensure_ascii= True)
    ready_to_push = solve_assignment(answer_json,datautf,debug)
    push_result = submit_assignment(ready_to_push["preSignedUrlAnswer"],ready_to_push["listAnswer"]) # type: ignore
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print("-"*20)
    print(f"Elapsed time solving for {student[0]}: {elapsed_time:.4f} seconds")
    print("-"*20)
    
    
    

