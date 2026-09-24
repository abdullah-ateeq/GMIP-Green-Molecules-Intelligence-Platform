from __future__ import annotations

from gmip.parsers.base_parser import BaseParser


class ParserRegistry:
    """
    Routes a source_id to the BaseParser responsible for it.

    See gmip.parsers.build_default_registry() for the concrete wiring of
    every source_id currently registered.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, type[BaseParser]] = {}

    def register(
        self,
        source_id: str,
        parser_cls: type[BaseParser],
    ) -> None:
        self._parsers[source_id] = parser_cls

    def has_parser(self, source_id: str) -> bool:
        return source_id in self._parsers

    def get_parser(self, source_id: str) -> BaseParser | None:
        parser_cls = self._parsers.get(source_id)

        if parser_cls is None:
            return None

        return parser_cls()
