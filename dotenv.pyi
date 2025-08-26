from os import PathLike
from typing import IO, Any, Optional, Union

def load_dotenv(
    dotenv_path: Optional[Union[str, PathLike[Any]]] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    override: bool = False,
    interpolate: bool = True,
    encoding: str = "utf-8",
) -> bool: ...