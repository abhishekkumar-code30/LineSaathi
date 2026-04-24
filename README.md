# 🚀 LineSaathi – Smart Queue Intelligence System

**LineSaathi** is a real-time smart queue monitoring system that tracks crowd occupancy using sensor data and provides live insights, predictions, and administrative controls.

Designed for places like **college mess, cafeterias, events, or service counters**, it helps reduce waiting time and improve crowd management.

---

## 📌 Features

### 🔴 Live Dashboard

* Real-time **occupancy tracking**
* Dynamic **crowd status (Low / Medium / High)**
* Visual **progress bar for capacity usage**
* Live **entry, exit, and net flow rates**
* Animated **crowd trend graph (Chart.js)**

### ⏳ Smart Insights

* Estimated **waiting time**
* **15-minute crowd prediction**
* **Rush hour detection**
* Best time suggestion to visit

### 🎛️ Admin Panel

* Set **maximum capacity**
* Reset:

  * Current count
  * Entry/Exit counters
  * Graph history
* Secure **admin login system**

### 🎨 UI/UX Highlights

* Dark & Light mode toggle 🌙☀️
* Glassmorphism (light mode)
* Premium black-gold theme (dark mode)
* Fully responsive layout

---

## 🛠️ Tech Stack

* **Frontend**: HTML, CSS, JavaScript
* **Backend**: Python (Flask)
* **Charts**: Chart.js
* **Styling**: Custom CSS + Tailwind (utility use)
* **Hardware**:

  * Arduino UNO
  * BreadBoard
  * Jumper Wires
  * 2 IR Sensors (Entry/Exit detection)

---

## 📁 Project Structure

```
LineSaathi/
│
├── app.py
│
├── Arduino_Code.txt
│
├── templates/
│   ├── index.html
│   ├── admin_panel.html
│   ├── admin_login.html
│
├── static/
│   ├── css/
│   │   ├── styleFP.css
│   │   ├── admin_panelSTYLE.css
│   │   ├── login.css
│   │
│   ├── js/
│       ├── scriptFP.js
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/abhishekkumar-code30/LineSaathi.git
cd LineSaathi
```

### 2️⃣ Install dependencies

```bash
pip install flask
```

### 3️⃣ Run the app

```bash
python app.py
```

### 4️⃣ Open in browser

```
http://127.0.0.1:5000
```

---

## 🔐 Admin Access

* Navigate to: `/admin`
* Enter admin password (defined in `app.py`)
* Access:

  * Capacity settings
  * Reset controls

---

## 🔌 Hardware Integration (Optional)

LineSaathi can be connected with:

* **2 IR Sensors**

  * Entry detection
  * Exit detection
* **Arduino**

  * Sends count data to Flask server

### Working Logic:

* Person crosses **Sensor 1 → Entry +1**
* Person crosses **Sensor 2 → Exit +1**
* Flask updates dashboard in real-time

---

## 📊 API Endpoints

| Endpoint       | Description                 |
| -------------- | --------------------------- |
| `/data`        | Returns live dashboard data |
| `/history`     | Returns graph history       |
| `/admin`       | Admin login                 |
| `/admin_panel` | Admin controls              |
| `/download`    | Download logs               |

---

## 🧠 Future Improvements

* AI-based prediction model 🤖
* Mobile app integration 📱
* Multi-location support 🌍
* Cloud database storage ☁️
* Notification alerts 🔔

---

## 👨‍💻 Author

**Abhishek Kumar**
Computer Science Student

---

## ⭐ Support

If you like this project:

* ⭐ Star the repo
* 🍴 Fork it
* 🚀 Build on top of it

---

## 📜 License

This project is open-source and available under the **Abhishek's License**.

---

> 💡 *LineSaathi aims to make queues smarter, faster, and stress-free.*
