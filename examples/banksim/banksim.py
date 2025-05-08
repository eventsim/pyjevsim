import time
import subprocess
import csv
import os

case = "classic"
# 실행할 파일 이름
file_name = f'banksim{case}.py'

# 실행 횟수
iterations = 10
#wiq_time = 50000

# CSV 파일에 기록 시작 (헤더 작성)
csv_file_path = f"./testcase_log_randomseed/{case}"
csv_file = f'{csv_file_path}/{case}_runtime.csv'

# 디렉터리와 파일 존재 여부 확인 후 없으면 생성
if not os.path.exists(csv_file_path):
    os.makedirs(csv_file_path)  # 디렉터리 생성

# CSV 파일이 없으면 헤더 작성
if not os.path.exists(csv_file):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([f'Execution Time {case}', 'Drop Count'])  # 헤더 작성

# 실행
for i in range(iterations):
    start_time = time.time()  # 시작 시간 기록
    with open('test.log', 'w', encoding='utf-8') as log_file:
        subprocess.run(['python', f'{file_name}'], stdout=log_file, stderr=subprocess.STDOUT)
    end_time = time.time()  # 종료 시간 기록

    execution_time = end_time - start_time  # 실행 시간 계산
    
    with open('./test.log', 'r', encoding='utf-8') as file:
        content = file.read()
        drop_count = content.count('Drop')

    # CSV 파일에 실행 시간 즉시 기록
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([execution_time, drop_count])  # 실행 번호와 실행 시간 기록

print(f'Execution times saved to {csv_file}')