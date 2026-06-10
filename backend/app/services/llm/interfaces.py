from abc import ABC, abstractmethod
from typing import Generator, Union

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        pass

    @abstractmethod
    def get_health_status(self) -> dict:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
