import gzip
from typing import Any, Optional, Dict

import jsonstreams

from kgx.config import get_logger
from kgx.sink import Sink


log = get_logger()


class JsonSink(Sink):
    """
    JsonSink is responsible for writing data as records
    to a JSON.

    Parameters
    ----------
    filename: str
        The filename to write to
    format: str
        The file format (``json``)
    compression: Optional[str]
        The compression type (``gz``)
    kwargs: Any
        Any additional arguments

    """

    def __init__(self, filename: str, format: str = 'json', compression: Optional[str] = None, **kwargs: Any):
        super().__init__()
        self.filename = filename
        if compression:
            self.compression = compression
        self.FH = jsonstreams.Stream(jsonstreams.Type.object, filename=filename)
        self.NH = None
        self.EH = None

    def write_node(self, record: Dict) -> None:
        """
        Write a node record to JSON.

        Parameters
        ----------
        record: Dict
            A node record

        """
        if not self.NH:
            self.NH = self.FH.subarray('nodes')
        self.NH.write(record)

    def write_edge(self, record: Dict) -> None:
        """
        Write an edge record to JSON.

        Parameters
        ----------
        record: Dict
            An edge record

        """
        if not self.EH:
            self.EH = self.FH.subarray('edges')
        self.EH.write(record)

    def finalize(self) -> None:
        """
        Finalize by creating a compressed file, if needed.
        """
        if self.compression:
            WH = gzip.open(f"{self.filename}.gz", 'wb')
            with open(self.filename, 'r') as FH:
                for line in FH.buffer:
                    WH.write(line)

