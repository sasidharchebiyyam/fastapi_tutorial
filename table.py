from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Tuple
import random
import pandas as pd

app = FastAPI()

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
time_slots = [f"{h}:00" for h in range(8, 22)]  

class TimetableRequest(BaseModel):
    subjects: List[str]
    weekly_hours: Dict[str, int]
    available_slots: List[Tuple[str, str]]  # List of (day, time)

@app.post("/generate-timetable")
def generate_timetable(request: TimetableRequest):
    subjects = request.subjects
    weekly_hours = request.weekly_hours
    available_slots = request.available_slots

    if not subjects or not available_slots:
        raise HTTPException(status_code=400, detail="Subjects and available slots are required")

    task_pool = []
    for subject, hours in weekly_hours.items():
        task_pool.extend([subject] * hours)

    random.shuffle(task_pool)

    timetable = pd.DataFrame("", index=days, columns=time_slots)
    slot_idx = 0

    for task in task_pool:
        if slot_idx >= len(available_slots):
            break
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

    return timetable.fillna("").to_dict()
