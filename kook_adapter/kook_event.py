import asyncio
from collections.abc import Coroutine
from typing import Any

from astrbot import logger
from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.message_components import File, Image, Plain, Video
from astrbot.api.platform import AstrBotMessage, PlatformMetadata
from astrbot.core.message.components import At, AtAll, BaseMessageComponent, Reply

from .kook_client import KookClient
from .kook_types import (
    KookMessageType,
    OrderMessage,
)


class KookEvent(AstrMessageEvent):
    def __init__(
        self,
        message_str: str,
        message_obj: AstrBotMessage,
        platform_meta: PlatformMetadata,
        session_id: str,
        client: KookClient,
    ):
        super().__init__(message_str, message_obj, platform_meta, session_id)
        self.client = client
        self.channel_id = message_obj.group_id or message_obj.session_id
        self._file_message_counter = 0

    def _warp_message(
        self, index: int, messageComponent: BaseMessageComponent
    ) -> Coroutine[Any, Any, OrderMessage]:
        async def wrap_upload(
            index: int, message_type: KookMessageType, upload_coro
        ) -> OrderMessage:
            url = await upload_coro
            return OrderMessage(index=index, text=url, type=message_type)

        async def handle_plain(
            index: int,
            text: str | None,
            reply_id: str | int = "",
        ):
            if not text:
                text = ""
            return OrderMessage(
                index=index,
                text=text,
                type=KookMessageType.KMARKDOWN,
                reply_id=reply_id,
            )

        match messageComponent:
            case Image():
                self._file_message_counter += 1
                return wrap_upload(
                    index,
                    KookMessageType.IMAGE,
                    self.client.upload_asset(messageComponent.file),
                )

            case Video():
                self._file_message_counter += 1
                return wrap_upload(
                    index,
                    KookMessageType.VIDEO,
                    self.client.upload_asset(messageComponent.file),
                )
            case File():

                async def handle_file(idx=index, f_item=messageComponent):
                    f_data = await f_item.get_file()
                    url = await self.client.upload_asset(f_data)
                    return OrderMessage(index=idx, text=url, type=KookMessageType.FILE)

                self._file_message_counter += 1
                return handle_file()
            case Plain():
                return handle_plain(index, messageComponent.text)
            case At():
                return handle_plain(index, f"(met){messageComponent.qq}(met)")
            case AtAll():
                return handle_plain(index, "(met)all(met)")
            case Reply():
                return handle_plain(
                    index, messageComponent.text, reply_id=messageComponent.id
                )
            case _:
                raise NotImplementedError(
                    f'kook适配器尚未实现对 "{messageComponent.type}" 消息类型的支持'
                )

    async def send(self, message: MessageChain):

        file_upload_tasks: list[Coroutine[Any, Any, OrderMessage]] = []
        for index, item in enumerate(message.chain):
            file_upload_tasks.append(self._warp_message(index, item))

        if self._file_message_counter > 0:
            logger.debug("[Kook] 正在向kook服务器上传文件")
        order_messages = await asyncio.gather(*file_upload_tasks)
        order_messages.sort(key=lambda x: x.index)

        reply_id: str | int = ""
        for item in order_messages:
            if item.reply_id:
                reply_id = item.reply_id
            if not item.text:
                logger.debug(f'[Kook] 跳过空消息,类型为"{item.type}"')
                continue
            await self.client.send_text(self.channel_id, item.text, item.type, reply_id)

        await super().send(message)
