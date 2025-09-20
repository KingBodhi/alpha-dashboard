"""
Alpha Protocol Network - Web Server
FastAPI-based web server with proper async architecture.
"""
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from .config import APNConfig
from .logging_config import get_logger

logger = get_logger("web_server")

# Pydantic Models
class NodeConfig(BaseModel):
    nodeId: str
    publicKey: str
    paymentAddress: str
    roles: List[str]
    settings: dict = {}

class MessageRequest(BaseModel):
    text: str
    dest_id: str = "broadcast"

class APNWebServer:
    """APN Web Server with proper async architecture"""
    
    def __init__(self, config: APNConfig, radio_manager):
        self.config = config
        self.radio_manager = radio_manager
        self.app = self._create_app()
        self.server = None
        
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="Alpha Protocol Network",
            description="Decentralized mesh communication network",
            version="0.2.0"
        )
        
        # Setup routes
        self._setup_routes(app)
        
        return app
    
    def _setup_routes(self, app: FastAPI):
        """Setup all API routes"""
        
        @app.get("/", response_class=HTMLResponse)
        async def landing_page(request: Request):
            """APN node landing page"""
            status = await self._get_node_status()
            
            # Simple HTML response for now
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Alpha Protocol Network Node</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                           background: linear-gradient(135deg, #000000, #1a1a1a);
                           color: #FFD700; margin: 0; padding: 2rem; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .header {{ text-align: center; margin-bottom: 2rem; }}
                    .logo {{ font-size: 3rem; font-weight: bold; margin-bottom: 1rem; }}
                    .card {{ background: rgba(255,215,0,0.1); border: 1px solid #FFD700; 
                            border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }}
                    .status {{ display: flex; justify-content: space-between; }}
                    .online {{ color: #00ff00; }}
                    .offline {{ color: #ff0000; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Α</div>
                        <h1>Alpha Protocol Network</h1>
                        <p>Sovereign Mesh Communication Node</p>
                    </div>
                    
                    <div class="card">
                        <h2>Node Status</h2>
                        <div class="status">
                            <span>Node ID:</span>
                            <span>{status['node_id']}</span>
                        </div>
                        <div class="status">
                            <span>Status:</span>
                            <span class="{'online' if status['running'] else 'offline'}">
                                {'Online' if status['running'] else 'Offline'}
                            </span>
                        </div>
                        <div class="status">
                            <span>Active Radios:</span>
                            <span>{len(status['radios'])}</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Services</h2>
                        {"".join(f'<div class="status"><span>{k.title()}:</span><span class="{"online" if v else "offline"}">{"Enabled" if v else "Disabled"}</span></div>' for k, v in status['services'].items())}
                    </div>
                    
                    <div class="card">
                        <h2>API Endpoints</h2>
                        <ul>
                            <li><a href="/config" style="color: #FFD700;">/config</a> - Node configuration</li>
                            <li><a href="/status" style="color: #FFD700;">/status</a> - Node status</li>
                            <li><a href="/peers" style="color: #FFD700;">/peers</a> - Known peers</li>
                            <li><a href="/docs" style="color: #FFD700;">/docs</a> - API documentation</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        
        @app.get("/config", response_model=NodeConfig)
        async def get_node_config():
            """Get node configuration"""
            return NodeConfig(
                nodeId=self.config.identity.node_id,
                publicKey=self.config.identity.public_key,
                paymentAddress=self.config.identity.payment_address,
                roles=self.config.services.roles,
                settings={
                    "storage": {
                        "availableGB": self.config.services.storage_gb,
                        "pricePerGB": self.config.services.storage_price_per_gb
                    } if self.config.services.storage_enabled else {},
                    "compute": {
                        "cores": self.config.services.compute_cores,
                        "pricePerSecond": self.config.services.compute_price_per_second
                    } if self.config.services.compute_enabled else {},
                    "bridge": {
                        "region": self.config.services.bridge_region,
                        "pricePerMB": self.config.services.bridge_price_per_mb
                    } if self.config.services.bridge_enabled else {}
                }
            )
        
        @app.get("/status")
        async def get_status():
            """Get node status"""
            return await self._get_node_status()
        
        @app.get("/peers")
        async def get_peers():
            """Get known peers"""
            return {"peers": self.config.network.known_peers}
        
        @app.post("/register")
        async def register_peer(peer: NodeConfig):
            """Register a new peer"""
            # TODO: Add signature verification
            peer_url = f"{peer.nodeId}:8000"
            if peer_url not in self.config.network.known_peers:
                self.config.network.known_peers.append(peer_url)
                self.config.save()
                logger.info(f"Registered new peer: {peer.nodeId}")
                
            return {"message": f"Peer {peer.nodeId} registered successfully"}
        
        @app.post("/message")
        async def send_message(msg: MessageRequest, background_tasks: BackgroundTasks):
            """Send a message via radio"""
            background_tasks.add_task(self._send_message, msg.text, msg.dest_id)
            return {"message": "Message queued for transmission"}
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}
    
    async def _get_node_status(self) -> Dict[str, Any]:
        """Get comprehensive node status"""
        # This will be implemented by service_manager
        return {
            "node_id": self.config.identity.node_id,
            "running": True,
            "radios": [],
            "services": {
                "relay": self.config.services.relay_enabled,
                "storage": self.config.services.storage_enabled,
                "compute": self.config.services.compute_enabled,
                "bridge": self.config.services.bridge_enabled,
            }
        }
    
    async def _send_message(self, text: str, dest_id: str):
        """Send message via radio manager"""
        try:
            from .radio_manager import RadioMessage
            message = RadioMessage(
                source_id=self.config.identity.node_id,
                dest_id=dest_id,
                message_type="text",
                payload=text.encode('utf-8')
            )
            
            success = await self.radio_manager.send_message(message)
            if success:
                logger.info(f"Message sent successfully: {text[:50]}...")
            else:
                logger.error("Failed to send message")
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the web server"""
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_config=None,  # Use our logging config
            access_log=False
        )
        self.server = uvicorn.Server(config)
        
        logger.info(f"Starting web server on {host}:{port}")
        await self.server.serve()
    
    async def stop(self):
        """Stop the web server"""
        if self.server:
            logger.info("Stopping web server")
            self.server.should_exit = True
