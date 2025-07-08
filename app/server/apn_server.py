import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# -----------------------------
# SETUP
# -----------------------------
app = FastAPI(title="Alpha Protocol Network Registry")

APN_DIR = Path.home() / ".apn"
NODE_CONFIG_PATH = APN_DIR / "node_config.json"
REGISTRY_PATH = APN_DIR / "registry.json"

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# -----------------------------
# Pydantic Model
# -----------------------------
class NodeConfig(BaseModel):
    nodeId: str
    paymentAddress: str
    roles: List[str]
    settings: dict = {}


# -----------------------------
# Helper Functions
# -----------------------------
def load_own_config() -> dict:
    if NODE_CONFIG_PATH.exists():
        with NODE_CONFIG_PATH.open() as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Node config not found.")


def load_registry() -> List[dict]:
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open() as f:
            return json.load(f)
    return []


def save_registry(registry: List[dict]):
    APN_DIR.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("w") as f:
        json.dump(registry, f, indent=2)


# -----------------------------
# Routes
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    try:
        node = load_own_config()
    except HTTPException:
        node = {
            "nodeId": "Unknown",
            "paymentAddress": "Unavailable",
            "roles": [],
            "settings": {}
        }

    return templates.TemplateResponse("landing.html", {"request": request, "node": node})


@app.get("/config", response_model=NodeConfig)
def get_own_config():
    return load_own_config()


@app.get("/registry", response_model=List[NodeConfig])
def get_registry():
    registry = load_registry()
    own = load_own_config()

    # Ensure own config is always included
    if not any(node.get("nodeId") == own.get("nodeId") for node in registry):
        registry.insert(0, own)

    return registry


@app.post("/register")
def register_peer(peer: NodeConfig):
    registry = load_registry()

    # Check for duplicates by nodeId
    for existing in registry:
        if existing.get("nodeId") == peer.nodeId:
            raise HTTPException(status_code=400, detail="Node already registered.")

    registry.append(peer.dict())
    save_registry(registry)

    return {"message": f"Node '{peer.nodeId}' registered successfully."}
