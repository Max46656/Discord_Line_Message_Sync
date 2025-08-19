import aiohttp
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def keep_alive_task(webhook_url: str):
    #每 14 分鐘訪問webhook以維持Render不下線。
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(webhook_url) as response:
                    if response.status == 200:
                        logger.info(f"Keep-alive: 成功訪問 webhook URL，狀態碼 {response.status}")
                    else:
                        logger.error(f"Keep-alive: 訪問 webhook URL 失敗，狀態碼 {response.status}")
                await asyncio.sleep(14 * 60)
            except Exception as e:
                logger.error(f"Keep-alive 失敗: {e}")
                await asyncio.sleep(60)