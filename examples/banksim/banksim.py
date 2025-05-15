import time
import subprocess
import csv
import os
import re
import sys

#name_list = ["classic", "model_snapshot", "model_restore",
#        "snapshot", "restore"]

name_list = ["snapshot", "restore"]

#wiq_time = "10000"
wiq_time = int(sys.argv[1])
gen_num = ["20", "10", "30"] ## case1, case2, case3

# 실행 횟수
iterations = 1

for i in range(iterations) :
    for name in name_list :
        case = 3
        
        for j in range(len(gen_num)) :
            file_name = f"banksim_{name}_case{j+1}"
            python_name = f"banksim_{name}"

            file_path = f"./output/{wiq_time}"
            csv_file = f'{file_path}/csv/{file_name}.csv'
                
            if not os.path.exists(f"{file_path}/csv"):
                os.makedirs(f"{file_path}/csv")  # 디렉터리 생성        

            if not os.path.exists(f"{file_path}/output"):
                os.makedirs(f"{file_path}/output")  # 디렉터리 생성    
                
            if not os.path.exists(csv_file):
                with open(csv_file, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([f'Execution Time{python_name}', 'Accountant user Count', 'Drop Count'])  # 헤더 작성

            with open(f'{file_path}/output/{wiq_time}_{file_name}_{i}.log', 'w', encoding='utf-8') as log_file:
                start_time = time.time()
                subprocess.run(['python3', f'{python_name}.py', str(wiq_time), str(gen_num[j])], stdout=log_file, stderr=subprocess.STDOUT)
                end_time = time.time()  # 종료 시간 기록
            
            run_time = end_time - start_time  # 실행 시간 계산
            
            with open(f"{file_path}/output/{wiq_time}_{file_name}_{i}.log", 'r') as file:
                for line in file:
                    if "Accountant user" in line:
                        acc_user_match = re.search(r"Accountant user\s*:\s*(\d+)", line)
                        if acc_user_match:
                            accountant_user = int(acc_user_match.group(1))

                    elif "Dropped user" in line:
                        drop_user_match = re.search(r"Dropped user\s*:\s*(\d+)", line)
                        if drop_user_match:
                            dropped_user = int(drop_user_match.group(1))

            # CSV 파일에 실행 시간 즉시 기록
            with open(csv_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                if "snapshot" in name :
                    writer.writerow([run_time])  # 실행 번호와 실행 시간 기록
                else : 
                    writer.writerow([run_time, accountant_user, dropped_user])  # 실행 번호와 실행 시간 기록