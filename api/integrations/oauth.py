from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import logging
import urllib.parse
from pydantic import BaseModel
from fastapi import BackgroundTasks

import config
from db.database import get_global_db
from api.integrations.shopify import fetch_shopify_catalog

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Shopify OAuth"])

class ShopifySyncRequest(BaseModel):
    store_domain: str
    access_token: str

@router.get("/install")
async def install(shop: str):
    """
    Step 1 of OAuth: Redirect merchant to Shopify to approve app installation.
    """
    if not shop:
        raise HTTPException(status_code=400, detail="Missing shop parameter")
        
    if not config.SHOPIFY_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Missing SHOPIFY_CLIENT_ID in server configuration")

    # Scopes required by the AI Salesman Hub
    scopes = "read_products,read_inventory,read_script_tags,write_script_tags"
    redirect_uri = f"{config.PUBLIC_API_URL}/v1/shopify/callback"
    
    auth_url = (
        f"https://{shop}/admin/oauth/authorize?"
        f"client_id={config.SHOPIFY_CLIENT_ID}&"
        f"scope={scopes}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}"
    )
    
    return RedirectResponse(url=auth_url)

@router.get("/v1/shopify/callback")
async def callback(shop: str, code: str, request: Request, background_tasks: BackgroundTasks):
    """
    Step 2 of OAuth: Shopify redirects back with an authorization code.
    Exchange code for permanent access_token.
    """
    if not shop or not code:
        raise HTTPException(status_code=400, detail="Missing shop or code")

    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": config.SHOPIFY_CLIENT_ID,
        "client_secret": config.SHOPIFY_CLIENT_SECRET,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=payload)
        
        if response.status_code != 200:
            logger.error(f"Failed to get access token: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to retrieve access token from Shopify")
            
        data = response.json()
        access_token = data.get("access_token")

    if not access_token:
        raise HTTPException(status_code=500, detail="No access token in response")

    # Save to global DB
    try:
        with get_global_db() as conn:
            conn.execute(
                """
                INSERT INTO shopify_installations (shop_domain, access_token) 
                VALUES (%s, %s) 
                ON CONFLICT (shop_domain) 
                DO UPDATE SET access_token = EXCLUDED.access_token, installed_at = CURRENT_TIMESTAMP
                """,
                (shop, access_token)
            )
            logger.info(f"Successfully saved OAuth token for {shop}")
    except Exception as e:
        logger.error(f"Failed to save token to DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to save token to database")

    # Trigger background catalog sync automatically upon installation
    try:
        from api.main import shopify_sync
        sync_req = ShopifySyncRequest(store_domain=shop, access_token=access_token)
        # Using a background task so the merchant isn't waiting on the loading screen
        background_tasks.add_task(shopify_sync, req=sync_req, background_tasks=background_tasks)
    except Exception as e:
        logger.error(f"Could not trigger background sync: {e}")

    # Redirect to a success page or back to Shopify Admin
    return {"status": "success", "message": f"Successfully installed AI Salesman on {shop}. Catalog sync has begun in the background!"}
