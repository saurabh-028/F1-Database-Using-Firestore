# F1-Database-Using-Firestore

FastAPI web app for managing an **F1 knowledge base** on **Google Cloud Firestore** with **Firebase login**, server-rendered Jinja templates, and CRUD for **Drivers** and **Teams**—plus dashboards, ad-hoc queries, and change logs.&#x20;

## ✨ Features

* **Auth via Firebase ID token (cookie)** with login/logout guard on write routes.&#x20;
* **Drivers & Teams CRUD**: add, edit/rename, delete; renames cascade to related docs.&#x20;
* **Dashboard** with totals, champions count, and **recent activity** feed.&#x20;
* **Query builders**: filter drivers/teams with `==, <, >, <=, >=` operators.&#x20;
* **Data bootstrap**: load sample data from `data/teams.json` and `data/drivers.json`.&#x20;

## 🧱 Tech Stack

* **FastAPI**, **Jinja2**, **StaticFiles** for the web app
* **Google Cloud Firestore (Native mode)** as DB
* **Firebase Authentication** (verifies `token` cookie on the server)&#x20;

## 📁 Project Layout

```
.
├─ main.py
├─ templates/              # login.html, dashboard.html, drivers.html, teams.html, etc.
├─ static/                 # css/js/assets
├─ data/
│   ├─ drivers.json
│   └─ teams.json
└─ serviceAccount.json     # GCP service account key (local dev)
```

## ⚙️ Setup (Local)

1. **Python deps**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn google-cloud-firestore google-auth google-auth-oauthlib jinja2
```

2. **Google credentials**

   * Download a **service account JSON** with Firestore access and save as `serviceAccount.json`.
   * Ensure the env var is set (the app also sets it for you):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=serviceAccount.json
```

The app creates a Firestore client at startup.&#x20;

3. **Firebase Auth (frontend)**

   * Your login page should set a **`token` cookie** with the Firebase ID token after a successful sign-in.
   * The backend verifies this cookie on protected routes.&#x20;

4. **Run**

```bash
uvicorn main:app --reload
```

5. **Test Firestore connection**

```
GET /test-firebase   -> {"connected_to_project": "<your-project-id>"}
```

(Uses the Firestore client created from your credentials.)&#x20;

## 🧰 Core Collections

* `drivers` – `{name, age, total_pole_positions, total_race_wins, total_points_scored, total_world_titles, total_fastest_laps, team}`
* `teams` – `{name, principal, championships, base, year_founded, total_pole_positions, total_race_wins, previous_season_position}`
* `recent_activity` – `{action, details, timestamp}` (server timestamps; used on dashboard).&#x20;

## 🔗 Routes (high level)

### Public / Read

* `GET /` → redirects to **Dashboard**
* `GET /dashboard` → totals, champions count, recent activity&#x20;
* `GET /drivers` · `GET /teams` → list pages
* `GET /driver/{driver_name}` · `GET /team/{team_name}` → detail pages&#x20;
* `GET /query-drivers` · `POST /query-drivers` → filter drivers by attribute + operator + value
* `GET /query-teams` · `POST /query-teams` → filter teams similarly&#x20;

### Auth Required (token cookie)

* `GET /add-driver` · `POST /add-driver` (unique name check)
* `POST /delete-driver/{driver_name}`
* `GET /edit-driver/{driver_name}` · `POST /update-driver/{driver_name}` (supports renaming)
* `GET /add-team` · `POST /add-team` (unique name check)
* `POST /delete-team/{team_name}`
* `GET /edit-team/{team_name}` · `POST /update-team/{team_name}` (renaming updates all related drivers)
* `GET /initialize-data` → loads JSON from `data/` into Firestore (admin/bootstrap).&#x20;

### Auth Flow

* `GET /login` → login page; if already authenticated, redirects to `/`
* `GET /logout` → clears `token` cookie and redirects to `/`&#x20;

## 📝 Notes & Gotchas

* **Unique IDs by name**: Drivers/Teams are stored under document IDs matching their `name`. Renaming handles **copy+delete** (driver) or **cascade updates** (team → drivers).&#x20;
* **Type casting in queries**: numeric fields are cast before Firestore `where` filters; invalid input is handled gracefully.&#x20;
* **Recent activity** is automatically logged for add/update/delete operations.&#x20;

## 🚀 Deploy

* Any ASGI host (e.g., Uvicorn/Gunicorn on VM/Container).
* For GCP, use **Cloud Run** with Workload Identity to avoid local keys.
* Ensure frontend sets the Firebase ID token cookie for protected routes.
