import pandas as pd
import argparse
import os


def main(args):
    # Load your data
    file = args.input
    if os.path.exists(file):
        data = pd.read_csv(file)
    else:
        print(f"File {file} does not exist.")
        return

    # Convert the 'time' column to datetime
    data['time'] = pd.to_datetime(data['time'])

    # Extract seconds and milliseconds
    data['second'] = data['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    # Convert microseconds to milliseconds
    data['millisecond'] = data['time'].dt.microsecond // 100000
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check time data for completeness.")
    parser.add_argument('--input', type=str, help='Input CSV file path')
    args = parser.parse_args()
    main(args)
