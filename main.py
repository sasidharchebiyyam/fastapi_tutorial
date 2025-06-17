from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple
import pandas as pd
import random

app = FastAPI(title="Study Timetable Generator")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIME_SLOTS = [f"{h}:00" for h in range(8, 22)]  # 8 AM to 9 PM

class TimetableRequest(BaseModel):
    subjects: Dict[str, int]  # subject -> hours
    available_slots: List[Tuple[str, str]]  # list of (day, time) tuples

@app.post("/generate-timetable/")
def generate_timetable(request: TimetableRequest):
    subjects = request.subjects
    available_slots = request.available_slots

    if not subjects:
        raise HTTPException(status_code=400, detail="Subjects cannot be empty")
    if not available_slots:
        raise HTTPException(status_code=400, detail="No available time slots provided")

    # Build the task pool
    task_pool = []
    for subject, hours in subjects.items():
        task_pool.extend([subject] * hours)

    random.shuffle(task_pool)

    # Initialize timetable
    timetable = pd.DataFrame("", index=DAYS, columns=TIME_SLOTS)
    slot_idx = 0

    for task in task_pool:
        if slot_idx >= len(available_slots):
            return {"warning": "Not enough available slots for all subject hours!"}

        day, time = available_slots[slot_idx]
        if timetable.loc[day, time] == "":
            timetable.loc[day, time] = task
            slot_idx += 1
        else:
            while slot_idx < len(available_slots) and timetable.loc[available_slots[slot_idx][0], available_slots[slot_idx][1]] != "":
                slot_idx += 1
            if slot_idx < len(available_slots):
                day, time = available_slots[slot_idx]
                timetable.loc[day, time] = task
                slot_idx += 1

    # Return the timetable as a dictionary
    return timetable.fillna("").to_dict()