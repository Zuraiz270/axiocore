import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from src.stream_consumer import stream_consumer_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background Redis stream consumer
    logger.info("FastAPI Worker starting up...")
    
    stop_event = asyncio.Event()
    consumer_task = asyncio.create_task(stream_consumer_loop(stop_event))
    
    yield
    
    # Shutdown
    logger.info("FastAPI Worker shutting down...")
    stop_event.set()
    await consumer_task

app = FastAPI(title="Axiocore V3 Worker", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "python-worker"}
