from typing import Any

class _Sentiment:
    polarity: float
    subjectivity: float

class TextBlob:
    def __init__(self, text: str, *args: Any, **kwargs: Any) -> None: ...
    @property
    def sentiment(self) -> _Sentiment: ...