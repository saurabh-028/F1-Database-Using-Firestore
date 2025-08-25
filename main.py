from fastapi import FastAPI, Request, Form, Depends, HTTPException
from google.cloud import firestore
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
import os
from google.auth.transport import requests
from typing import List, Dict
import json
from pathlib import Path
from fastapi import HTTPException

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceAccount.json"
db = firestore.Client()

templates = Jinja2Templates(directory="templates")
firebase_request_adapter = requests.Request()

# Helper functions
def get_driver_collection():
    return db.collection("drivers")

@app.get("/test-firebase")
async def test_firebase():
    project_id = db.project
    return {"connected_to_project": project_id}

def get_team_collection():
    return db.collection("teams")

def get_recent_activity_collection():
    return db.collection("recent_activity")

def log_activity(action: str, details: str):
    activity_ref = get_recent_activity_collection()
    activity_ref.add({
        "action": action,
        "details": details,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def get_user_token(request: Request):
    id_token = request.cookies.get("token")
    user_token = None
    if id_token:
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as err:
            print(str(err))
    return user_token

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user_token = get_user_token(request)
    return await dashboard(request, user_token)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user_token = get_user_token(request)
    if user_token:
        return RedirectResponse(url="/")
    return templates.TemplateResponse('login.html', {'request': request})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("token")
    return response


# Dashboard route
@app.get("/dashboard")
async def dashboard(request: Request, user_token: Dict = Depends(get_user_token)):
    # Get stats for dashboard
    drivers = get_driver_collection().stream()
    teams = get_team_collection().stream()
    
    total_drivers = len(list(drivers))
    total_teams = len(list(teams))
    
    champions = [doc.to_dict() for doc in get_driver_collection().where("total_world_titles", ">", 0).stream()]
    total_champions = len(champions)
    
    recent_activity = [doc.to_dict() for doc in get_recent_activity_collection().order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_token": user_token,
        "total_drivers": total_drivers,
        "total_teams": total_teams,
        "total_champions": total_champions,
        "recent_activity": recent_activity
    })

# Driver routes
@app.get("/drivers")
async def drivers_page(request: Request, user_token: Dict = Depends(get_user_token)):
    drivers = [doc.to_dict() for doc in get_driver_collection().stream()]
    return templates.TemplateResponse("drivers.html", {
        "request": request,
        "user_token": user_token,
        "drivers": drivers
    })

@app.get("/add-driver")
async def add_driver_page(request: Request, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        return RedirectResponse(url="/login")
    
    teams = [doc.to_dict()["name"] for doc in get_team_collection().stream()]
    return templates.TemplateResponse("add_driver.html", {
        "request": request,
        "user_token": user_token,
        "teams": teams
    })

@app.post("/add-driver")
async def add_driver(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    pole_positions: int = Form(...),
    race_wins: int = Form(...),
    points: int = Form(...),
    world_titles: int = Form(...),
    fastest_laps: int = Form(...),
    team: str = Form(...),
    user_token: Dict = Depends(get_user_token)
):
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    drivers_ref = get_driver_collection()
    
    # Check if driver already exists
    existing_driver = drivers_ref.document(name).get()
    if existing_driver.exists:
        raise HTTPException(status_code=400, detail="Driver with this name already exists")
    
    drivers_ref.document(name).set({
        "name": name,
        "age": age,
        "total_pole_positions": pole_positions,
        "total_race_wins": race_wins,
        "total_points_scored": points,
        "total_world_titles": world_titles,
        "total_fastest_laps": fastest_laps,
        "team": team
    })
    
    log_activity("Driver Added", f"Added new driver: {name}")
    return RedirectResponse("/drivers", status_code=302)

@app.post("/delete-driver/{driver_name}")
async def delete_driver(driver_name: str, request: Request, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    drivers_ref = get_driver_collection()
    
    # Verify driver exists before deleting
    driver_doc = drivers_ref.document(driver_name).get()
    if not driver_doc.exists:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    drivers_ref.document(driver_name).delete()
    
    log_activity("Driver Deleted", f"Deleted driver: {driver_name}")
    return RedirectResponse("/drivers", status_code=302)

# Team routes
@app.get("/teams")
async def teams_page(request: Request, user_token: Dict = Depends(get_user_token)):
    teams = [doc.to_dict() for doc in get_team_collection().stream()]
    return templates.TemplateResponse("teams.html", {
        "request": request,
        "user_token": user_token,
        "teams": teams
    })

@app.get("/add-team")
async def add_team_page(request: Request, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("add_team.html", {"request": request, "user_token": user_token})

@app.post("/add-team")
async def add_team(
    request: Request,
    name: str = Form(...),
    principal: str = Form(...),
    championships: int = Form(...),
    base: str = Form(...),
    founded: int = Form(...),
    user_token: Dict = Depends(get_user_token)
):
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    teams_ref = get_team_collection()
    
    # Check if team already exists
    existing_team = teams_ref.document(name).get()
    if existing_team.exists:
        raise HTTPException(status_code=400, detail="Team with this name already exists")
    
    teams_ref.document(name).set({
        "name": name,
        "principal": principal,
        "championships": championships,
        "base": base,
        "founded": founded
    })
    
    log_activity("Team Added", f"Added new team: {name}")
    return RedirectResponse("/teams", status_code=302)

@app.post("/delete-team/{team_name}")
async def delete_team(team_name: str, request: Request, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    teams_ref = get_team_collection()
    
    # Verify team exists before deleting
    team_doc = teams_ref.document(team_name).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    teams_ref.document(team_name).delete()
    
    log_activity("Team Deleted", f"Deleted team: {team_name}")
    return RedirectResponse("/teams", status_code=302)

# Comparison route
@app.get("/compare")
async def compare_page(request: Request, user_token: Dict = Depends(get_user_token)):
    drivers = [doc.to_dict() for doc in get_driver_collection().stream()]
    teams = [doc.to_dict() for doc in get_team_collection().stream()]
    
    # Ensure we have enough drivers and teams for comparison
    if len(drivers) < 2:
        drivers = []
    if len(teams) < 2:
        teams = []
    
    return templates.TemplateResponse("compare.html", {
        "request": request,
        "user_token": user_token,
        "drivers": drivers,
        "teams": teams
    })

#  query drivers route
@app.get("/query-drivers", response_class=HTMLResponse)
async def query_drivers_page(request: Request, user_token: Dict = Depends(get_user_token)):
    return templates.TemplateResponse("query_drivers.html", {
        "request": request,
        "user_token": user_token,
        "drivers": []
    })

@app.post("/query-drivers", response_class=HTMLResponse)
async def query_drivers(
    request: Request,
    attribute: str = Form(...),
    operator: str = Form(...),
    value: str = Form(...),
    user_token: Dict = Depends(get_user_token)
):
    drivers_ref = get_driver_collection()
    
    try:
        # Convert value to proper type based on attribute
        if attribute in ["age", "total_pole_positions", "total_race_wins", 
                        "total_points_scored", "total_world_titles", "total_fastest_laps"]:
            value = int(value)
        
        # Build the query based on operator
        if operator == "eq":
            query = drivers_ref.where(attribute, "==", value)
        elif operator == "lt":
            query = drivers_ref.where(attribute, "<", value)
        elif operator == "gt":
            query = drivers_ref.where(attribute, ">", value)
        elif operator == "lte":
            query = drivers_ref.where(attribute, "<=", value)
        elif operator == "gte":
            query = drivers_ref.where(attribute, ">=", value)
        else:
            raise ValueError("Invalid operator")
        
        drivers = [doc.to_dict() for doc in query.stream()]
        
    except Exception as e:
        drivers = []
        print(f"Query error: {str(e)}")
    
    return templates.TemplateResponse("query_drivers.html", {
        "request": request,
        "user_token": user_token,
        "drivers": drivers,
        "form_data": {
            "attribute": attribute,
            "operator": operator,
            "value": value
        }
    })

# Driver detail page
@app.get("/driver/{driver_name}", response_class=HTMLResponse)
async def driver_detail(request: Request, driver_name: str):
    driver_ref = get_driver_collection().document(driver_name)
    driver = driver_ref.get().to_dict()
    
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return templates.TemplateResponse("driver_detail.html", {
        "request": request,
        "driver": driver,
        "user_token": get_user_token(request)
    })

# Team detail page
@app.get("/team/{team_name}", response_class=HTMLResponse)
async def team_detail(request: Request, team_name: str):
    team_ref = get_team_collection().document(team_name)
    team = team_ref.get().to_dict()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get drivers for this team
    drivers = [doc.to_dict() for doc in get_driver_collection().where("team", "==", team_name).stream()]
    
    return templates.TemplateResponse("team_detail.html", {
        "request": request,
        "team": team,
        "drivers": drivers,
        "user_token": get_user_token(request)
    })

# Team query (similar to driver query)
@app.get("/query-teams", response_class=HTMLResponse)
async def query_teams_page(request: Request):
    return templates.TemplateResponse("query_teams.html", {
        "request": request,
        "user_token": get_user_token(request),
        "teams": []
    })

@app.post("/query-teams", response_class=HTMLResponse)
async def query_teams(
    request: Request,
    attribute: str = Form(...),
    operator: str = Form(...),
    value: str = Form(...)
):
    teams_ref = get_team_collection()
    
    try:
        # Convert value to proper type
        if attribute in ["year_founded", "total_pole_positions", "total_race_wins", 
                       "total_constructor_titles", "previous_season_position"]:
            value = int(value)
        
        # Build query
        if operator == "eq":
            query = teams_ref.where(attribute, "==", value)
        elif operator == "lt":
            query = teams_ref.where(attribute, "<", value)
        elif operator == "gt":
            query = teams_ref.where(attribute, ">", value)
        elif operator == "lte":
            query = teams_ref.where(attribute, "<=", value)
        elif operator == "gte":
            query = teams_ref.where(attribute, ">=", value)
        
        teams = [doc.to_dict() for doc in query.stream()]
        
    except Exception as e:
        teams = []
        print(f"Team query error: {str(e)}")
    
    return templates.TemplateResponse("query_teams.html", {
        "request": request,
        "user_token": get_user_token(request),
        "teams": teams,
        "form_data": {
            "attribute": attribute,
            "operator": operator,
            "value": value
        }
    })

# Initialize data route
@app.get("/initialize-data")
async def initialize_data(request: Request, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Load team data
        teams_path = Path(__file__).parent / "data" / "teams.json"
        with open(teams_path) as f:
            teams_data = json.load(f)
        
        # Load driver data
        drivers_path = Path(__file__).parent / "data" / "drivers.json"
        with open(drivers_path) as f:
            drivers_data = json.load(f)
        
        # Initialize counters
        teams_added = 0
        drivers_added = 0
        
        # Add teams
        teams_ref = db.collection("teams")
        for team in teams_data:
            teams_ref.document(team["name"]).set(team)
            teams_added += 1
        
        # Add drivers
        drivers_ref = db.collection("drivers")
        for driver in drivers_data:
            drivers_ref.document(driver["name"]).set(driver)
            drivers_added += 1
        
        return {
            "status": "success",
            "message": "Database initialized successfully",
            "teams_added": teams_added,
            "drivers_added": drivers_added
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
    # Update Driver Routes
@app.get("/edit-driver/{driver_name}")
async def edit_driver_page(request: Request, driver_name: str, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        return RedirectResponse(url="/login")
    
    driver_ref = get_driver_collection().document(driver_name)
    driver = driver_ref.get().to_dict()
    teams = [doc.to_dict()["name"] for doc in get_team_collection().stream()]
    
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return templates.TemplateResponse("edit_driver.html", {
        "request": request,
        "driver": driver,
        "teams": teams,
        "user_token": user_token
    })


@app.post("/update-driver/{driver_name}")
async def update_driver(
    request: Request,
    driver_name: str,
    name: str = Form(...),
    age: int = Form(...),
    pole_positions: int = Form(...),
    race_wins: int = Form(...),
    points: int = Form(...),
    world_titles: int = Form(...),
    fastest_laps: int = Form(...),
    team: str = Form(...),
    user_token: Dict = Depends(get_user_token)
):
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    drivers_ref = get_driver_collection()
    
    # Verify original driver exists
    original_driver = drivers_ref.document(driver_name).get()
    if not original_driver.exists:
        raise HTTPException(status_code=404, detail="Original driver not found")
    
    # If name is being changed, check new name doesn't exist
    if driver_name != name:
        new_driver = drivers_ref.document(name).get()
        if new_driver.exists:
            raise HTTPException(status_code=400, detail="Driver with new name already exists")
    
    driver_data = {
        "name": name,
        "age": age,
        "total_pole_positions": pole_positions,
        "total_race_wins": race_wins,
        "total_points_scored": points,
        "total_world_titles": world_titles,
        "total_fastest_laps": fastest_laps,
        "team": team
    }
    
    # If name changed, create new document and delete old one
    if driver_name != name:
        drivers_ref.document(name).set(driver_data)
        drivers_ref.document(driver_name).delete()
    else:
        drivers_ref.document(driver_name).update(driver_data)
    
    log_activity("Driver Updated", f"Updated driver: {name}")
    return RedirectResponse(f"/driver/{name}", status_code=302)

# Update Team Routes
@app.get("/edit-team/{team_name}")
async def edit_team_page(request: Request, team_name: str, user_token: Dict = Depends(get_user_token)):
    if not user_token:
        return RedirectResponse(url="/login")
    
    team_ref = get_team_collection().document(team_name)
    team = team_ref.get().to_dict()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return templates.TemplateResponse("edit_team.html", {
        "request": request,
        "team": team,
        "user_token": user_token
    })

@app.post("/update-team/{team_name}")
async def update_team(
    request: Request,
    team_name: str,
    name: str = Form(...),
    principal: str = Form(...),
    championships: int = Form(...),
    base: str = Form(...),
    founded: int = Form(...),
    poles: int = Form(...),
    wins: int = Form(...),
    position: int = Form(...),
    user_token: Dict = Depends(get_user_token)
):
    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    teams_ref = get_team_collection()
    
    # Verify original team exists
    original_team = teams_ref.document(team_name).get()
    if not original_team.exists:
        raise HTTPException(status_code=404, detail="Original team not found")
    
    # If name is being changed, check new name doesn't exist
    if team_name != name:
        new_team = teams_ref.document(name).get()
        if new_team.exists:
            raise HTTPException(status_code=400, detail="Team with new name already exists")
    
    team_data = {
        "name": name,
        "principal": principal,
        "championships": championships,
        "base": base,
        "year_founded": founded,
        "total_pole_positions": poles,
        "total_race_wins": wins,
        "previous_season_position": position
    }
    
    # If name changed, update all drivers from this team
    if team_name != name:
        # Update team document
        teams_ref.document(name).set(team_data)
        teams_ref.document(team_name).delete()
        
        # Update all drivers from this team
        drivers_ref = get_driver_collection()
        drivers = drivers_ref.where("team", "==", team_name).stream()
        for driver in drivers:
            drivers_ref.document(driver.id).update({"team": name})
    else:
        teams_ref.document(team_name).update(team_data)
    
    log_activity("Team Updated", f"Updated team: {name}")
    return RedirectResponse(f"/team/{name}", status_code=302)