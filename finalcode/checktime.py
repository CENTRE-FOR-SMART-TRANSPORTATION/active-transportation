import pandas as pd

# Load your data
data = pd.read_csv('2025-04-23_12-41-39/witmotion_data_1.csv')

# Convert the 'time' column to datetime
data['time'] = pd.to_datetime(data['time'])

# Extract seconds and milliseconds
data['second'] = data['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
data['millisecond'] = data['time'].dt.microsecond // 100000  # Convert microseconds to milliseconds
print(data.head())
# Group by second and collect all milliseconds
grouped = data.groupby('second')['millisecond'].apply(set)

# Check for each second if it has all milliseconds from 0 to 999
results = {}
for second, milliseconds in grouped.items():
    results[second] = all(ms in milliseconds for ms in range(10))

# Print results
for second, has_all in results.items():
    if has_all:
        print(f"{second} has all milliseconds.")
    else:
        print(f"{second} is missing some milliseconds.")
