import os

target = "c:/Users/admin/Desktop/AI_salesman_plugin/api/main.py"
with open(target, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip() == 'if audio is not None:':
        end_idx = i
        break

new_lines = lines[:125]

code = """

# App

app = FastAPI(
    title="Voice Shopping Agent API",
    description="Voice-enabled AI shopping assistant powered by OpenAI.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for demo; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if config.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestTracingMiddleware)

# Endpoints

@app.get("/health", response_model=HealthResponse, tags=["Utility"])
async def health():
    \"\"\"Check API and model configuration health.\"\"\"
    return HealthResponse(
        status="ok",
        models={
            "stt": config.STT_MODEL,
            "llm": config.LLM_MODEL,
            "tts": f"{config.TTS_MODEL} / {config.TTS_VOICE}",
            "embedding": config.EMBEDDING_MODEL,
        },
    )

@app.post("/v1/admin/crawler/run", tags=["Utility"])
async def trigger_crawler():
    \"\"\"Manually trigger the crawler.\"\"\"
    import config
    import asyncio
    import concurrent.futures
    from agent.ingestion import sync_web_crawl
    
    target_url = config.CURRENT_URL
    site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if not target_url:
        return {"status": "error", "message": "No CURRENT_URL configured."}

    logger.info("Manual crawler trigger requested for %s...", target_url)

    def run_sync():
        try:
            sync_web_crawl(
                target_url,
                max_pages=config.CRAWL_MAX_PAGES,
                max_depth=config.CRAWL_MAX_DEPTH,
                site_id=site_id,
                reconcile_missing=True,
                source_name="custom_url_crawler"
            )
        except Exception as e:
            logger.error("Manual crawl failed: %s", e)

    loop = asyncio.get_running_loop()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, run_sync)
    
    return {"status": "ok", "message": "Crawler started in background."}

@app.post("/v1/client-log", tags=["Utility"])
async def client_log(req: ClientLogRequest):
    \"\"\"Receive browser-side diagnostics from the injected widget.\"\"\"
    safe_event = str(req.event)[:80]
    safe_payload = {
        str(key)[:80]: str(value)[:300]
        for key, value in (req.payload or {}).items()
    }
    logger.info("CLIENT | %s | %s", safe_event, safe_payload)
    return {"status": "ok"}

@app.post("/v1/shop", response_model=ShopResponse, tags=["Shopping Agent"])
async def shop(
    site_id: str = Form(config.DEFAULT_SITE_ID, description="Site ID for multi-tenancy"),
    audio: Optional[UploadFile] = File(
        None, description="Audio file (WAV, MP3, WebM, OGG)"
    ),
    text: Optional[str] = Form(
        None, description="Text input (for testing without audio)"
    ),
    skip_tts: bool = Form(False, description="Skip TTS to reduce latency (testing)"),
    conversation_history: Optional[str] = Form(
        None, description="JSON array of prior conversation turns"
    ),
):
    \"\"\"
    **Main endpoint.** Send customer audio or text → receive UI actions + voice response.

    - **audio**: Upload a recorded audio clip of the customer's voice.
    - **text**: Alternatively, send plain text (useful for debugging).
    - **skip_tts**: Set to `true` to skip speech synthesis (faster, text-only response).

    Returns:
    - `transcript` — what the customer said
    - `response_text` — what ShopBot says back
    - `ui_actions` — list of website control commands for the frontend
    - `audio_b64` — base64-encoded WAV of the spoken response
    \"\"\"
    if audio is None and (text is None or text.strip() == ""):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either an audio file or text input.",
        )

    audio_bytes: Optional[bytes] = None
    audio_filename = "audio.wav"

"""

new_lines.extend(code.splitlines(True))
new_lines.extend(lines[end_idx:])

with open(target, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
