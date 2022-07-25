import asyncio
from async_timeout import timeout
from asyncprawcore import RequestException


class MergeAsyncIterator:
    def __init__(self, *it, time_out=60, maxsize=0):
        self._it = [self.iter_coro(i) for i in it]
        self.timeout = time_out
        self._futures = []
        self._queue = asyncio.Queue(maxsize=maxsize)

    def __aiter__(self):
        for it in self._it:
            f = asyncio.ensure_future(it)
            self._futures.append(f)
        return self

    async def __anext__(self):
        if all(f.done() for f in self._futures) and self._queue.empty():
            return None
        with timeout(self.timeout):
            try:
                return await self._queue.get()
            except asyncio.CancelledError:
                return None

    def iter_coro(self, it):
        if not hasattr(it, '__aiter__'):
            raise ValueError('Object passed must be an AsyncIterable')
        return self.aiter_to_queue(it)

    async def aiter_to_queue(self, ait):
        try:
            async for i in ait:
                await self._queue.put(i)
                await asyncio.sleep(0)
        except RequestException as e:
            return None
