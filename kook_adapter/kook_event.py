import asyncio
from types import CoroutineType
from typing import Any

from astrbot import logger
from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.message_components import File, Image, Plain, Video
from astrbot.api.platform import AstrBotMessage, PlatformMetadata
from astrbot.core.message.components import At, AtAll, Music

from .kook_client import KookClient
from .kook_types import (
    KookMessageType,
    OrderMessage,
)

class KookEvent(AstrMessageEvent):
    def __init__(self, message_str: str, message_obj: AstrBotMessage, platform_meta: PlatformMetadata, session_id: str, client: KookClient):
        super().__init__(message_str, message_obj, platform_meta, session_id)
        self.client = client
        self.channel_id = message_obj.group_id or message_obj.session_id

    async def send(self, message: MessageChain):

        async def wrap_upload(
            index: int, message_type: KookMessageType, upload_coro
        ) -> OrderMessage:
            url = await upload_coro
            return OrderMessage(index=index, message=url, type=message_type)

        async def handle_plain(index: int, text: str | None):
            if not text:
                text = ""
            return OrderMessage(
                index=index, message=text, type=KookMessageType.KMARKDOWN
            )

        file_task_counter = 0
        file_upload_tasks: list[CoroutineType[Any, Any, OrderMessage]] = []
        for index, item in enumerate(message.chain):
            match item:
                case Image():
                    file_upload_tasks.append(
                        wrap_upload(
                            index,
                            KookMessageType.IMAGE,
                            self.client.upload_asset(item.file),
                        )
                    )
                    file_task_counter += 1
                case Video():
                    file_upload_tasks.append(
                        wrap_upload(
                            index,
                            KookMessageType.VIDEO,
                            self.client.upload_asset(item.file),
                        )
                    )
                    file_task_counter += 1
                case File():

                    async def handle_file(idx=index, f_item=item):
                        f_data = await f_item.get_file()
                        url = await self.client.upload_asset(f_data)
                        return OrderMessage(
                            index=idx, message=url, type=KookMessageType.FILE
                        )

                    file_upload_tasks.append(handle_file())
                    file_task_counter += 1
                case Plain():
                    file_upload_tasks.append(handle_plain(index, item.text))

                case At():
                    # file_upload_tasks.append(handle_plain(index, f"@{item.name}"))
                    file_upload_tasks.append(
                        handle_plain(index, f"(met){item.qq}(met)")
                    )
                case AtAll():
                    # file_upload_tasks.append(handle_plain(index, f"@{item.name}"))
                    file_upload_tasks.append(handle_plain(index, "(met)all(met)"))

        if file_task_counter > 0:
            logger.debug("[Kook] 正在向kook服务器上传文件")
        order_messages = await asyncio.gather(*file_upload_tasks)
        order_messages.sort(key=lambda x: x.index)

        for item in order_messages:
            await self.client.send_text(self.channel_id, item.message, item.type)

        await super().send(message)
