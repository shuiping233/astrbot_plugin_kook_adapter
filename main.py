from astrbot.api.star import Context, Star


class KookAdapterPlugin(Star):
    def __init__(self, context: Context):
        from .kook_adapter.kook_adapter import KookPlatformAdapter  # noqa
