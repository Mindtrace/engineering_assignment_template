"""Client-side helper class for communicating with any ServerBase server."""

import json
import logging
from uuid import UUID
from typing import List

from fastapi import HTTPException
import requests
from urllib3.util.url import parse_url, Url

from mindtrace import Config
from mindtrace.services.base import Heartbeat, ServerStatus
from mindtrace.utils import ifnone


class ConnectionManagerBase:
    """Client-side helper class for communicating with Mindtrace servers."""

    config = Config()
    logger = logging.getLogger()
    name = "Mindtrace Application ConnectionManager"

    def __init__(self, url: Url | None = None, server_id: UUID | None = None, server_pid_file: str | None = None):
        super().__init__()
        self.url = ifnone(url, default=parse_url("http://localhost:8080/"))
        self._server_id = server_id
        self._server_pid_file = server_pid_file

    @property
    def endpoints(self) -> List[str]:
        """Get the list of registered endpoints on the server."""
        response = requests.request("POST", str(self.url) + "endpoints", timeout=60)
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.content)
        return json.loads(response.content)["endpoints"]

    @property
    def status(self) -> ServerStatus:
        """Get the status of the server."""
        try:
            response = requests.request("POST", str(self.url) + "status", timeout=60)
            if response.status_code != 200:
                return ServerStatus.Down
            else:
                return ServerStatus(json.loads(response.content)["status"])
        except Exception as e:
            self.logger.warning(f"Failed to get status of server at {self.url}: {e}")
            return ServerStatus.Down

    def heartbeat(self) -> Heartbeat:
        """Get the heartbeat of the server.

        The heartbeat includes the server's status, as well as any additional diagnostic information the server may
        provide.
        """
        response = requests.request("POST", str(self.url) + "heartbeat", timeout=60)
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.content)
        response = json.loads(response.content)["heartbeat"]
        return Heartbeat(
            status=ServerStatus(response["status"]),
            server_id=response["server_id"],
            message=response["message"],
            details=response["details"],
        )

    @property
    def server_id(self) -> UUID:
        """Get the server's unique id."""
        if self._server_id is not None:
            return self._server_id
        else:
            response = requests.request("POST", str(self.url) + "server_id", timeout=60)
            if response.status_code != 200:
                raise HTTPException(response.status_code, response.content)
            self._server_id = UUID(json.loads(response.content)["server_id"])
            return self._server_id

    @property
    def pid_file(self) -> str:
        """Get the server's pid file."""
        if self._server_pid_file is not None:
            return self._server_pid_file
        else:
            response = requests.request("POST", str(self.url) + "pid_file", timeout=60)
            if response.status_code != 200:
                raise HTTPException(response.status_code, response.content)
            return json.loads(response.content)["pid_file"]

    def shutdown(self):
        """Shutdown the server.

        Example::

            from mindtrace.services import ServerBase, ServerStatus

            cm = ServerBase.launch()
            assert cm.status == ServerStatus.Available

            cm.shutdown()
            assert cm.status == ServerStatus.Down
        """
        response = requests.request("POST", str(self.url) + "shutdown", timeout=60)
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.content)
        return response

    def __enter__(self):
        self.logger.debug({f"Initializing {self.name} as a context manager."})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f"Shutting down {self.name} Server.")
        try:
            self.shutdown()
        finally:
            if exc_type is not None:
                info = (exc_type, exc_val, exc_tb)
                self.logger.exception("Exception occurred", exc_info=info)
                return self.suppress
        return False
