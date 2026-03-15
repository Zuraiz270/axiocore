import asyncio
import logging
from src.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class ReviewLockManager:
    def __init__(self):
        self.redis = get_redis_client()
        self.lock_expiry_ms = 15000 # 15 seconds absolute expiration
        
    def _lock_key(self, tenant_id: str, document_id: str) -> str:
        return f"review_lock:{tenant_id}:{document_id}"

    async def acquire_lock(self, tenant_id: str, document_id: str, reviewer_id: str) -> bool:
        """
        Attempts to acquire an exclusive lock on the document for the reviewer.
        Utilizes Redis SET NX PX to guarantee atomicity.
        """
        key = self._lock_key(tenant_id, document_id)
        
        # NX = Only set if it does not exist
        # PX = Expire in milliseconds
        acquired = await self.redis.set(key, reviewer_id, nx=True, px=self.lock_expiry_ms)
        
        if acquired:
            logger.info(f"Lock ACQUIRED by {reviewer_id} on {document_id}")
            return True
        else:
            # Document is already locked by someone else
            current_owner = await self.redis.get(key)
            logger.warning(f"Lock DENIED for {reviewer_id} on {document_id} - currently held by {current_owner}")
            return False

    async def extend_lock(self, tenant_id: str, document_id: str, reviewer_id: str) -> bool:
        """
        Extends the heartbeat. Checks if the lock is still held by the same reviewer
        using a Lua script to guarantee atomicity.
        """
        key = self._lock_key(tenant_id, document_id)
        
        # Lua script: If the value matches the calling reviewer, extend the TTL.
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("pexpire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self.redis.eval(script, 1, key, reviewer_id, self.lock_expiry_ms)
        
        if result == 1:
            logger.debug(f"Lock EXTENDED by {reviewer_id} on {document_id}")
            return True
        else:
            logger.warning(f"Lock EXTENSION FAILED for {reviewer_id} on {document_id}")
            return False

    async def release_lock(self, tenant_id: str, document_id: str, reviewer_id: str) -> bool:
        """
        Releases the lock manually upon review completion or cancellation.
        """
        key = self._lock_key(tenant_id, document_id)
        
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(script, 1, key, reviewer_id)
        
        if result == 1:
            logger.info(f"Lock RELEASED by {reviewer_id} on {document_id}")
            return True
        else:
            logger.warning(f"Lock RELEASE FAILED for {reviewer_id} on {document_id}")
            return False
