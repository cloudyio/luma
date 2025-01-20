import asyncio
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class QueueItem:
    action: str
    params: Dict[str, Any]
    future: asyncio.Future

class QueueManager:
    def __init__(self):
        self.queue = asyncio.Queue()
        
    async def add_task(self, action: str, **params) -> Any:
        future = asyncio.Future()
        await self.queue.put(QueueItem(action=action, params=params, future=future))
        return await future
    
    async def get_task(self) -> QueueItem:
        return await self.queue.get()
    
    def task_done(self):
        self.queue.task_done()

queue_manager = QueueManager()
