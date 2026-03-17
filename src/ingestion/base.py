from abc import ABC, abstractmethod
import asyncio

class BaseConnector(ABC):
    @abstractmethod
    async def run(self, queue: asyncio.Queue) -> None:
        raise NotImplementedError
