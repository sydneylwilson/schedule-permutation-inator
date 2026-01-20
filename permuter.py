import pandas as pd
from datetime import datetime, timedelta
import sys, os 
from collections import Counter
import numpy as np

# Hard code the names of people who should be schedule with someone else, makes it less likely (but not impossible) 
# for them to be scheduled in the first round, so they can be added manually later 
# NOTE: These should match the when2meet names
INEXPERIENCED = [""]

# Remove from the list anyone who does not have at least 1 hour of availability listed
def get_active_people(df):
    people = df.columns.drop("time")
    active = []

    for p in people:
        if df[p].notna().any():
            active.append(p)

    return active

# Read in CSV
def load_csv(path):
    return pd.read_csv(path)

# When2meet stores time in UTC and 12-hour clock (quite the interesting combination), therefore normalize it to EST and 24-hour clock
def normalize_times(df):
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])
    min_hour = int(df["time"].dt.hour.min())
    offset_hours = (10 - min_hour) % 24
    df["time"] = df["time"] + pd.Timedelta(hours=int(offset_hours))
    return df

# Put together each hour block for the schedule
def build_hour_blocks(df):
    df = normalize_times(df)
    df = df.sort_values("time")
    people = df.columns.drop("time").tolist()
    # for this subset of people, once again sort the inexperienced people to last
    people = sorted(people, key=lambda x: x in INEXPERIENCED)
    availability_by_slot = {}

    for _, row in df.iterrows():
        time = row["time"]
        available = [p for p in people if pd.notna(row[p])]
        availability_by_slot[time] = set(available)
    start_date = df["time"].dt.date.min()
    end_date = df["time"].dt.date.max()
    dates = []
    current = start_date

    while current <= end_date:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    hour_blocks = []
    availability = {}

    for d in dates:
        for hour in range(10, 19): # 10 AM to 6 PM
            block_start = pd.Timestamp(datetime.combine(d, datetime.min.time()) + timedelta(hours=hour))
            slots = [
                block_start + pd.Timedelta(minutes=0),
                block_start + pd.Timedelta(minutes=15),
                block_start + pd.Timedelta(minutes=30),
                block_start + pd.Timedelta(minutes=45),
            ]
            available_people = None
            for s in slots:
                if s not in availability_by_slot:
                    available_people = set()
                    break
                if available_people is None:
                    available_people = availability_by_slot[s].copy()
                else:
                    available_people &= availability_by_slot[s]

            if available_people:
                hour_blocks.append(block_start)
                availability[block_start] = sorted(list(available_people))

    for hour in availability:
        availability[hour] = sorted(
            availability[hour],
            key=lambda x: x in INEXPERIENCED
        )

    return hour_blocks, availability

# Maximize how many different people are on the schedule (first pass should incorporate as many as possible 
# since we can always manually add more later)
def score_schedule(schedule):
    people = list(schedule.values())
    unique_people = len(set(people))
    counts = Counter(people)
    variance = np.var(list(counts.values()))
    return unique_people * 1000 - variance

# Generate the schedule using backtracking algorithm
def generate_schedules(hour_blocks, availability, max_schedules=500):
    people = set()

    for v in availability.values():
        people.update(v)

    people = sorted(list(people))
    total_hours = {p: 0 for p in people}
    daily_hours = {p: {} for p in people}
    schedules = []

    def backtrack(i, current_schedule, last_person, consecutive_count):
        if len(schedules) >= max_schedules:
            return

        if i == len(hour_blocks):
            schedules.append(current_schedule.copy())
            return

        hour = hour_blocks[i]
        day = hour.date()

        for person in availability.get(hour, []):
            if total_hours[person] >= 4:
                continue
            if daily_hours[person].get(day, 0) >= 2:
                continue
            if person == last_person and consecutive_count >= 2:
                continue

            current_schedule[hour] = person
            total_hours[person] += 1
            daily_hours[person][day] = daily_hours[person].get(day, 0) + 1

            if person == last_person:
                backtrack(i + 1, current_schedule, person, consecutive_count + 1)
            else:
                backtrack(i + 1, current_schedule, person, 1)

            total_hours[person] -= 1
            daily_hours[person][day] -= 1

            if daily_hours[person][day] == 0:
                del daily_hours[person][day]

            current_schedule.pop(hour)

            if len(schedules) >= max_schedules:
                return

    backtrack(0, {}, None, 0)
    schedules_scored = [(score_schedule(s), s) for s in schedules]
    schedules_scored.sort(reverse=True, key=lambda x: x[0])

    return [s for _, s in schedules_scored]

# Print to console stats on how many people were scheduled and list those who were not scheduled (to be manually added later)
def print_schedule_stats(schedule, all_people):
    scheduled_people = set(schedule.values())
    unscheduled_people = sorted(list(all_people - scheduled_people))
    print("--------------------------------------------------")
    print(f"Scheduled {len(scheduled_people)} / {len(all_people)} people")
    print("Unscheduled:", ", ".join(unscheduled_people) if unscheduled_people else "None")

# Build the dataframe for exporting
def save_schedule(schedule, output_path):
    rows = []
    for hour, person in sorted(schedule.items()):
        rows.append({"time": hour, "person": person})
    pd.DataFrame(rows).to_csv(output_path, index=False)

def main(csv_path, max_schedules=50):
    df = load_csv(csv_path)
    hour_blocks, availability = build_hour_blocks(df)

    if not hour_blocks:
        print("No valid hour blocks found.")
        return

    print(f"Found {len(hour_blocks)} hour blocks.")
    schedules = generate_schedules(hour_blocks, availability, max_schedules=max_schedules)
    all_people = set(get_active_people(df))
    print(f"Generated {len(schedules)} schedules (max {max_schedules}).")

    base = os.path.splitext(os.path.basename(csv_path))[0]
    for i, sched in enumerate(schedules, start=1):
        print(f"\nSchedule #{i}")
        print_schedule_stats(sched, all_people)
        output_path = f"{base}_schedule_{i}.csv"
        save_schedule(sched, output_path)
        print(f"Saved {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python permuter.py when2meet_schedule.csv")
        sys.exit(1)
    csv_path = sys.argv[1]
    max_schedules = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    main(csv_path, max_schedules)
