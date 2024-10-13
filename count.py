file_path = 'log_restore_case2.txt'
#file_path = 'log_classic_case4.txt'
#file_path = 'log_snapshot.txt'
# Initialize a counter
drop_count = 0

# Open and read the file
with open(file_path, 'r') as file:
    # Iterate through each line in the file
    for line in file:
        # Count the occurrences of "Drop" (case-sensitive)
        drop_count += line.count("Drop")

print(drop_count)