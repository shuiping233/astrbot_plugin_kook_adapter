from dataclasses import dataclass
from enum import IntEnum


# 定义参见kook事件结构文档: https://developer.kookapp.cn/doc/event/event-introduction
class KookMessageType(IntEnum):
    TEXT = 1
    IMAGE = 2
    VIDEO = 3
    FILE = 4
    AUDIO = 8
    KMARKDOWN = 9
    CARD = 10
    SYSTEM = 255


@dataclass
class OrderMessage:
    index: int
    message: str
    type: KookMessageType
