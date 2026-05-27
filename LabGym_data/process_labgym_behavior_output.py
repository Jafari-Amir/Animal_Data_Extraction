import pandas as pd
import numpy as np
import ast

# Input and output files, 
INPUT_FILE = "all_event_probability.xlsx"

OUT_BINARY = "binary_event_data.xlsx"
OUT_SUMMARY = "behavior_count_duration.xlsx"

# Read LabGym output, which is usally is being generated with the name of all_event_probability.xlsx
raw = pd.read_excel(INPUT_FILE)
time_col = raw.columns[0]
pred_col = raw.columns[1]

# parse (rearrange) LabGym prediction column, example value you would see inside excell like:['move', 0.9917317]
def parse_label_prob(x):
    try:
        y = ast.literal_eval(str(x))
        if isinstance(y, (list, tuple)) and len(y) >= 2:
            return str(y[0]), float(y[1])
    except Exception:
        pass
    return "NA", np.nan
parsed = raw[pred_col].apply(parse_label_prob)
raw["LabGym_label"] = parsed.apply(lambda x: x[0])
raw["probability"] = parsed.apply(lambda x: x[1])

#Map LabGym labels to manuscript behavior names
label_map = {"elongation": "Stretching",
    "groom": "Grooming",
    "rearing": "Rearing",
    "stop": "Freezing",
    "turn": "Turning",
    "move": "Locomotion",
    "NA": None,
    #also you can add whatever needed as like sniffing
    }
behaviors = ["Stretching","Grooming","Rearing",
             "Freezing","Turning","Locomotion"]
#Create Binary event data (one-hot format) here,
binary = pd.DataFrame()
binary["time_sec"] = pd.to_numeric(raw[time_col], errors="coerce")
binary["LabGym_label"] = raw["LabGym_label"]
binary["probability"] = raw["probability"]
for behavior in behaviors:
    binary[behavior] = (raw["LabGym_label"].map(label_map) == behavior).astype(int)
#Save binary one-hot file
with pd.ExcelWriter(OUT_BINARY, engine="xlsxwriter") as writer:
    binary[["time_sec"] + behaviors].to_excel(
        writer,
        sheet_name="binary_one_hot",
        index=False)
    binary.to_excel(
        writer,
        sheet_name="binary_with_label_probability",
        index=False)
# Estimation of frame interval from time columns, and timestamps aren't assumed exactly 30 fps, it could be different 
time_values = binary["time_sec"].dropna()
if len(time_values) > 1 and time_values.iloc[-1] > time_values.iloc[0]:
    frame_interval = float(
        (time_values.iloc[-1] - time_values.iloc[0]) / (len(time_values) - 1))
else:
    frame_interval = 1/30 # our camera recording is 30fps and check yours too
estimated_fps = 1 / frame_interval
#Events or behaviors count and duration calculated here
#Behavioral event count was defined as the number of discrete behavioral bouts,
#where a new bout started when a given behavior changed from absent to present in the frame-wise binary time series.
summary_rows = []
for behavior in behaviors:
    x = binary[behavior].to_numpy()
    #Count a new event when behavior changes from 0 to 1
    event_count = int(((x == 1) & (np.r_[0, x[:-1]] == 0)).sum())
    frame_count = int(x.sum())
    duration_seconds = frame_count * frame_interval
    summary_rows.append({"Behavior": behavior,
        "Event_count": event_count,
        "Frame_count": frame_count,
        "Duration_seconds": duration_seconds,
        "Duration_minutes": duration_seconds / 60, #minutes is just easier for quick reading
        "Estimated_frame_interval_sec": frame_interval,
        "Estimated_fps": estimated_fps})
summary = pd.DataFrame(summary_rows)
# saving summary file
with pd.ExcelWriter(OUT_SUMMARY, engine="xlsxwriter") as writer:
    summary.to_excel(
        writer,
        sheet_name="count_duration",
        index=False)
    binary[["time_sec"] + behaviors].to_excel(
        writer,
        sheet_name="binary_one_hot",
        index=False)