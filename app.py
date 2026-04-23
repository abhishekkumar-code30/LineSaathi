from flask import Flask, render_template, jsonify, request, send_file, session, redirect, url_for
import serial
import threading
import time
from datetime import datetime, timedelta
import csv
import os
import json
from collections import deque

app = Flask(__name__)
app.secret_key = "linesaathi_super_secret_2026"

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
SERIAL_PORT  = 'COM7'       # ← Change if your Arduino is on a different port
BAUD_RATE    = 9600
DATA_FILE    = "settings.json"
CSV_LOG      = "linesaathi_log.csv"
data_lock    = threading.Lock()

# ──────────────────────────────────────────────
# SETTINGS  (capacity persists across restarts)
# ──────────────────────────────────────────────
def load_settings():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"capacity": 50}

def save_settings(settings):
    with open(DATA_FILE, 'w') as f:
        json.dump(settings, f)

config = load_settings()

# ──────────────────────────────────────────────
# SHARED STATE
# ──────────────────────────────────────────────
history = []          # [{time, current}, ...]  – last 100 readings for graph

# Rolling timestamps for rate calculations (last 10 minutes)
entry_timestamps = deque()   # Unix timestamps of each entry event
exit_timestamps  = deque()   # Unix timestamps of each exit event

# For rush hour: store (hour, count) pairs across sessions (in-memory)
hourly_peaks = {}   # { hour_str: max_count_seen }

latest_data = {
    "current":      0,
    "entry":        0,
    "exit":         0,
    "action":       "Waiting for sensor data...",
    "timestamp":    "--:--:--",
    "crowd_level":  "Less Crowd",
    "level_color":  "green",
    "occupancy":    0,
    "wait_time":    0,
    "wait_unit":    "min",
    "suggestion":   "System initializing. Please wait.",
    "predicted_15": 0,
    "rush_time":    "--:--",
    "best_window":  "Calculating...",
    "max_cap":      config["capacity"],
    "entry_rate":   0.0,   # people/min entering
    "exit_rate":    0.0,   # people/min leaving
    "net_rate":     0.0,
}

# ──────────────────────────────────────────────
# RATE CALCULATION  (rolling 5-minute window)
# ──────────────────────────────────────────────
RATE_WINDOW = 300  # seconds

def _clean_timestamps():
    cutoff = time.time() - RATE_WINDOW
    while entry_timestamps and entry_timestamps[0] < cutoff:
        entry_timestamps.popleft()
    while exit_timestamps and exit_timestamps[0] < cutoff:
        exit_timestamps.popleft()

def get_rates():
    """Returns (entry_rate, exit_rate) in people/minute over last 5 min."""
    _clean_timestamps()
    minutes = RATE_WINDOW / 60
    er = len(entry_timestamps) / minutes
    xr = len(exit_timestamps)  / minutes
    return round(er, 2), round(xr, 2)

# ──────────────────────────────────────────────
# WAIT TIME  (Little's Law enhanced)
# ──────────────────────────────────────────────
def calculate_wait_time(current, cap, exit_rate):
    """
    Uses service-rate based wait time:
      • If exit_rate known → W = L / μ  (Little's Law: queue length / service rate)
      • Capped to reasonable bounds
    Falls back to occupancy-based heuristic when no rate data.
    """
    if exit_rate > 0 and current > 0:
        # Queue length beyond comfortable capacity
        comfortable = max(1, cap * 0.40)
        queue_len   = max(0, current - comfortable)
        # Each "server slot" processes 1 person per (1/exit_rate) minutes
        wait = queue_len / exit_rate
        return round(min(wait, 120))   # cap at 2 hours
    # Fallback heuristic
    occ = (current / cap * 100) if cap > 0 else 0
    if occ >= 80: return round(current * 0.6)
    if occ >= 45: return round(current * 0.3)
    return 0

# ──────────────────────────────────────────────
# CROWD METRICS
# ──────────────────────────────────────────────
def calculate_metrics(current, exit_rate):
    cap = config["capacity"]
    if cap <= 0:
        return "Less Crowd", "green", 0, 0, "Ideal time to visit!"
    occ  = round((current / cap) * 100, 1)
    wait = calculate_wait_time(current, cap, exit_rate)

    if occ >= 80:
        return "Most Crowd",   "red",    occ, wait, "Very high crowd! Avoid if possible."
    if occ >= 45:
        return "Decent Crowd", "yellow", occ, wait, "Moderate crowd. Expect some wait."
    return     "Less Crowd",   "green",  occ, 0,    "Excellent time! Very less crowd right now."

# ──────────────────────────────────────────────
# FORECAST  (linear trend over last 10 readings)
# ──────────────────────────────────────────────
def get_forecast(entry_rate, exit_rate):
    """
    Predicts occupancy in 15 minutes using net flow rate.
    Rush hour = time at which crowd will hit ≥ 80 % capacity.
    """
    cap     = config["capacity"]
    current = latest_data["current"]
    net     = entry_rate - exit_rate            # net people/min

    # 15-minute prediction using net rate
    predicted_15 = max(0, min(cap, int(current + net * 15)))

    # Rush time: when will we hit 80% capacity?
    threshold = cap * 0.80
    if net > 0 and current < threshold:
        minutes_to_rush = (threshold - current) / net
        if minutes_to_rush <= 120:             # only show if within 2 hours
            rush_dt   = datetime.now() + timedelta(minutes=minutes_to_rush)
            rush_time = rush_dt.strftime("%I:%M %p")
        else:
            rush_time = "--:--"
    elif current >= threshold:
        rush_time = "Now"
    else:
        # Fallback: use historical peak hour
        rush_time = _historical_rush_hour()

    return predicted_15, rush_time

def _historical_rush_hour():
    """Returns the historical peak hour label based on tracked hourly_peaks."""
    if not hourly_peaks:
        return "--:--"
    peak_hour = max(hourly_peaks, key=hourly_peaks.get)
    try:
        h = int(peak_hour)
        suffix = "AM" if h < 12 else "PM"
        display = h if h <= 12 else h - 12
        return f"{display}:00 {suffix}"
    except Exception:
        return "--:--"

# ──────────────────────────────────────────────
# BEST VISITING WINDOW
# ──────────────────────────────────────────────
def best_visiting_window():
    hour = datetime.now().hour
    if   6  <= hour < 9:  return "🌅 Early Morning (6–9 AM) — Usually least crowded"
    elif 9  <= hour < 12: return "☀️ Mid-Morning (9 AM–12 PM) — Moderate, manageable crowd"
    elif 12 <= hour < 14: return "🍽 Lunch Hours (12–2 PM) — Peak rush, expect longer wait"
    elif 14 <= hour < 17: return "🧘 Afternoon (2–5 PM) — Crowd typically eases off"
    elif 17 <= hour < 20: return "🌆 Evening (5–8 PM) — Often busy, plan ahead"
    else:                 return "🌙 Late Evening / Night — Generally quieter"

# ──────────────────────────────────────────────
# AUTO-HISTORY TICKER  (keeps graph alive when no Arduino data)
# ──────────────────────────────────────────────
def _auto_history_ticker():
    """Every 10 seconds, if no new entry was added in last 10s, repeat current count."""
    last_len = 0
    while True:
        time.sleep(10)
        with data_lock:
            if len(history) == last_len and len(history) > 0:
                # Append current reading so graph keeps moving in time
                history.append({
                    "time":    datetime.now().strftime("%H:%M"),
                    "current": latest_data["current"]
                })
                if len(history) > 100:
                    history.pop(0)
            last_len = len(history)

threading.Thread(target=_auto_history_ticker, daemon=True).start()

# ──────────────────────────────────────────────
# SERIAL READER  (background thread)
# ──────────────────────────────────────────────
def read_serial():
    global latest_data, history
    prev_entry = 0
    prev_exit  = 0

    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"✅ Connected to {SERIAL_PORT}")

            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()

                if not line:
                    continue
                if not line.startswith("DATA:"):
                    continue

                # Remove "DATA:" prefix and split by comma
                data_part = line[5:]          # after "DATA:"
                if not data_part:
                    continue
                parts = [p.strip() for p in data_part.split(",")]
                if len(parts) < 3:
                    continue

                try:
                    # Format from Arduino: in_count, out_count, current_count, [action]
                    ent         = int(parts[0])   # total entry count
                    ext         = int(parts[1])   # total exit count
                    curr        = int(parts[2])   # current count
                    act         = parts[3].strip() if len(parts) > 3 else "UPDATE"
                except ValueError:
                    continue

                now_ts = time.time()

                # Detect new entry / exit events since last reading
                new_entries = max(0, ent - prev_entry)
                new_exits   = max(0, ext - prev_exit)
                for _ in range(new_entries):
                    entry_timestamps.append(now_ts)
                for _ in range(new_exits):
                    exit_timestamps.append(now_ts)
                prev_entry = ent
                prev_exit  = ext

                er, xr = get_rates()

                level, color, occ, wait, sugg = calculate_metrics(curr, xr)
                predicted, rush_time = get_forecast(er, xr)

                hour_key = str(datetime.now().hour)
                hourly_peaks[hour_key] = max(hourly_peaks.get(hour_key, 0), curr)

                with data_lock:
                    history.append({"time": datetime.now().strftime("%H:%M:%S"), "current": curr})
                    if len(history) > 100:
                        history.pop(0)

                    latest_data.update({
                        "current":      curr,
                        "entry":        ent,
                        "exit":         ext,
                        "action":       act,
                        "timestamp":    datetime.now().strftime("%H:%M:%S"),
                        "crowd_level":  level,
                        "level_color":  color,
                        "occupancy":    occ,
                        "wait_time":    wait,
                        "suggestion":   sugg,
                        "predicted_15": predicted,
                        "rush_time":    rush_time,
                        "best_window":  best_visiting_window(),
                        "max_cap":      config["capacity"],
                        "entry_rate":   er,
                        "exit_rate":    xr,
                        "net_rate":     round(er - xr, 2),
                    })

                # CSV log
                file_exists = os.path.isfile(CSV_LOG)
                with open(CSV_LOG, "a", newline="") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["Timestamp","Current","Entry","Exit","Level","EntryRate","ExitRate"])
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        curr, ent, ext, level, er, xr
                    ])

        except serial.SerialException as e:
            print(f"Serial Error: {e}. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 5s...")
            time.sleep(5)


threading.Thread(target=read_serial, daemon=True).start()

# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data")
def get_data():
    with data_lock:
        return jsonify(latest_data.copy())


@app.route("/history")
def get_history():
    with data_lock:
        return jsonify(list(history))


@app.route("/download")
def download_csv():
    if os.path.isfile(CSV_LOG):
        return send_file(CSV_LOG, as_attachment=True)
    return "No log data yet.", 404


# ── Admin ──────────────────────────────────────
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == "12345":
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        return render_template("admin_login.html", error="Wrong password. Try again.")
    return render_template("admin_login.html", error=None)


@app.route("/admin_panel", methods=["GET", "POST"])
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    message = None

    if request.method == "POST":
        # ── Save capacity ──────────────────────────
        if "save_capacity" in request.form:
            try:
                new_cap = int(request.form.get("capacity", 50))
                if new_cap < 1:
                    raise ValueError
                config["capacity"] = new_cap
                save_settings(config)
                with data_lock:
                    latest_data["max_cap"] = new_cap
                return redirect(url_for("index"))
            except (ValueError, TypeError):
                message = "❌ Invalid capacity. Enter a positive number."

        # ── Reset counters ─────────────────────────
        elif "reset_counts" in request.form:
            with data_lock:
                latest_data["current"]  = 0
                latest_data["entry"]    = 0
                latest_data["exit"]     = 0
                latest_data["occupancy"] = 0
                latest_data["wait_time"] = 0
                latest_data["crowd_level"] = "Less Crowd"
                latest_data["level_color"] = "green"
                latest_data["suggestion"]  = "System reset. Waiting for sensor data."
                latest_data["action"]      = "RESET"
                history.clear()
            entry_timestamps.clear()
            exit_timestamps.clear()
            hourly_peaks.clear()
            message = "✅ All counters and graph history have been reset successfully."

    return render_template("admin_panel.html", capacity=config["capacity"], message=message)


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 LineSaathi Web Dashboard")
    print("   Main  →  http://127.0.0.1:5000")
    print("   Admin →  http://127.0.0.1:5000/admin  (password: 12345)")
    app.run(host="0.0.0.0", port=5000, debug=False)