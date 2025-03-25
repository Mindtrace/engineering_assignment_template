"""ServiceBase class. Provides unified methods for all Mindtrace (micro)services."""

import atexit
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import psutil
import requests
import signal
import subprocess
from typing import Type, TypeVar
import uuid
from uuid import UUID

import fastapi
from fastapi import FastAPI, HTTPException
from urllib3.util.url import parse_url, Url

from mindtrace import Config
from mindtrace.services import ConnectionManagerBase, Heartbeat, ServerStatus
from mindtrace.utils import autolog, ifnone, ifnone_url, named_lambda, Timeout

T = TypeVar("T", bound="ServerBase")  # A generic variable that can be 'ServerBase', or any subclass.
C = TypeVar("C", bound="ConnectionManagerBase")  # '' '' '' 'ConnectionManagerBase', or any subclass.


class ServiceMeta(type):
    def __init__(cls, name, bases, attr_dict):
        super().__init__(name, bases, attr_dict)

    @property
    def unique_name(self) -> str:
        return self.__module__ + "." + self.__name__


class Service(metaclass=ServiceMeta):
    """Base class for all Mindtrace services."""

    _status = ServerStatus.Down
    _endpoints: list[str] = []
    _client_interface: Type[C] = ConnectionManagerBase
    _active_servers: dict[UUID, psutil.Process] = {}

    config = Config()
    logger = logging.getLogger()
    name = "Mindtrace Application"

    def __init__(
        self,
        *,
        url: str | Url | None = None,
        host: str | None = None,
        port: int | None = None,
        summary: str | None = None,
        description: str | None = None,
        terms_of_service: str | None = None,
        license_info: str | None = None,
    ):
        """Initialize server instance. This is for internal use by the launch() method.

        Args:
            url: Full URL string or Url object
            host: Host address (e.g. "localhost" or "192.168.1.100")
            port: Port number
            summary: Summary of the server
            description: Description of the server
            terms_of_service: Terms of service for the server
            license_info: License information for the server

        Warning: Services should be created via the ServerClass.launch() method. The __init__ method here should be
        considered private internal use.
        """
        super().__init__()
        self._status: ServerStatus = ServerStatus.Available
        self.id, self.pid_file = self._generate_id_and_pid_file()

        # Build URL with  priority:
        # 1. Explicit URL parameter
        # 2. Host/port parameters
        # 3. Default URL from config
        self._url = self.build_url(url=url, host=host, port=port)

        description = ifnone(description, default=f"{self.name} server.")
        version_str = "Mindtrace 1.0"

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan for the FastAPI app."""
            self.logger.info(f"Server {self.id} starting up.")
            yield
            await self.shutdown_cleanup()
            self.logger.info(f"Server {self.id} shut down.")

        self.app = FastAPI(
            title=self.name,
            description=description,
            summary=summary,
            version=version_str,
            terms_of_service=terms_of_service,
            license_info=license_info,
            lifespan=lifespan,
        )
        self.add_endpoint(path="/endpoints", func=named_lambda("endpoints", lambda: {"endpoints": self.endpoints}))
        self.add_endpoint(path="/status", func=named_lambda("status", lambda: {"status": self.status}))
        self.add_endpoint(path="/heartbeat", func=named_lambda("heartbeat", lambda: {"heartbeat": self.heartbeat()}))
        self.add_endpoint(path="/server_id", func=named_lambda("server_id", lambda: {"server_id": self.id}))
        self.add_endpoint(path="/pid_file", func=named_lambda("pid_file", lambda: {"pid_file": self.pid_file}))
        self.add_endpoint(path="/shutdown", func=self.shutdown, autolog_kwargs={"log_level": logging.DEBUG})

    @classmethod
    def _generate_id_and_pid_file(cls, unique_id: UUID | None = None, pid_file: str | None = None) -> tuple[UUID, str]:
        """Generate a unique_id and pid_file for the server.

        The logic used ensures that the pid_file contains the (human-readable) class name as well as the unique_id.
        """

        # The following logic assures that the pid_file contains the unique_id
        if unique_id is not None and pid_file is not None:
            if str(unique_id) not in pid_file:
                raise ValueError(f"unique_id {unique_id} not found in pid_file {pid_file}")
        elif unique_id is not None and pid_file is None:
            unique_id = unique_id
            pid_file = cls._server_id_to_pid_file(unique_id)
        elif unique_id is None and pid_file is not None:
            unique_id = cls._pid_file_to_server_id(pid_file)
            pid_file = pid_file
        else:  # unique_id is None and pid_file is None
            unique_id = uuid.uuid1()
            pid_file = cls._server_id_to_pid_file(unique_id)

        Path(pid_file).parent.mkdir(parents=True, exist_ok=True)
        return unique_id, pid_file

    @classmethod
    def _server_id_to_pid_file(cls, server_id: UUID) -> str:
        return os.path.join(Path("~/.cache/mindtrace/pid_files").expanduser().absolute(), f"{cls.__name__}_{server_id}_pid.txt")

    @classmethod
    def _pid_file_to_server_id(cls, pid_file: str) -> UUID:
        return UUID(pid_file.split("_")[-2])

    @classmethod
    def status_at_host(cls, url: str | Url, timeout: int = 60) -> ServerStatus:
        """Check the status of the service at the given host url.

        This command may be used to check if a service (including this one) is available at a given host, useful for
        determining when a service has been successfully launched.

        Args:
            url: The host URL of the service.
        """
        url = parse_url(url) if isinstance(url, str) else url
        try:
            response = requests.request("POST", str(url) + "/status", timeout=timeout)
        except requests.exceptions.ConnectionError:
            return ServerStatus.Down
        if response.status_code != 200:
            return ServerStatus.Down

        status = ServerStatus(response.json()["status"])
        return status

    @classmethod
    def connect(cls: Type[T], url: str | Url | None = None, timeout: int = 60) -> C:
        """Connect to an existing service.

        The returned connection manager is determined by the registered connection manager for the service. If one has
        not explicitly been registered, the default connection manager (ConnectionManagerBase) will be used.

        Args:
            url: The host URL of the service.

        Returns:
            A connection manager for the service.

        Raises:
            HTTPException: If the server fails to connect, an HTTPException will be raised with status code 503.
        """
        url = ifnone_url(url, default=cls.default_url())
        host_status = cls.status_at_host(url, timeout=timeout)
        if host_status == ServerStatus.Available:
            return cls._client_interface(url=url)
        raise HTTPException(status_code=503, detail=f"Server failed to connect: {host_status}")

    @classmethod
    def launch(
        cls: Type[T],
        *,
        url: str | Url | None = None,
        host: str | None = None,
        port: int | None = None,
        block: bool = False,
        num_workers: int = 1,
        wait_for_launch: bool = True,
        timeout: int = 60,
        progress_bar: bool = True,
        **kwargs,
    ):
        """Launch a new server instance.

        The server can be configured through either explicit URL parameters or through kwargs. All kwargs are passed
        directly to the server instance's __init__ method.

        Args:
            url: Full URL string or Url object (highest priority)
            host: Host address (used if url not provided)
            port: Port number (used if url not provided)
            block: If True, blocks the calling process and keeps the server running
            num_workers: Number of worker processes
            wait_for_launch: Whether to wait for server startup
            timeout: Timeout for server startup in seconds
            progress_bar: Show progress bar during startup
            **kwargs: Additional parameters passed to the server's __init__ method
        """
        # Build the launch URL with priority
        launch_url = cls.build_url(url=url, host=host, port=port)

        # Check that there is not already a service at the given URL
        try:
            existing_status = cls.status_at_host(launch_url)
            if existing_status != ServerStatus.Down:
                raise HTTPException(
                    status_code=400,
                    detail=f"Server {cls.unique_name} at {launch_url} is already running with status {existing_status}.",
                )
        except RuntimeError as e:
            cls.logger.warning(f"Another service is already running at {launch_url}. New service was NOT launched.")
            raise e

        # All kwargs (including URL params) go directly to init_params
        init_params = {"url": str(launch_url), **kwargs}

        # Create launch command
        server_id = uuid.uuid1()
        launch_command = [
            "python",
            "-m",
            "mindtrace.services.base.launcher",
            "-s",
            cls.unique_name,
            "-w",
            str(num_workers),
            "-b",
            f"{launch_url.host}:{launch_url.port}",
            "-p",
            cls._server_id_to_pid_file(server_id),
            "-k",
            "uvicorn.workers.UvicornWorker",
            "--init-params",
            json.dumps(init_params),
        ]
        cls.logger.warning(f'Launching {cls.unique_name} with command: "{launch_command}"')
        process = subprocess.Popen(launch_command)

        # Register cleanup if this is the first server
        cls._active_servers[server_id] = process
        if len(cls._active_servers) == 1:
            atexit.register(cls._cleanup_all_servers)
            signal.signal(signal.SIGTERM, lambda sig, frame: cls._cleanup_all_servers())
            signal.signal(signal.SIGINT, lambda sig, frame: cls._cleanup_all_servers())

        # Wait for server to be available and get connection manager
        connection_manager = None
        if wait_for_launch:
            timeout_handler = Timeout(
                timeout=timeout,
                exceptions=(ConnectionRefusedError, requests.exceptions.ConnectionError, HTTPException),
                progress_bar=progress_bar,
                desc=f"Launching {cls.unique_name.split('.')[-1]} at {launch_url}",
            )
            try:
                connection_manager = timeout_handler.run(cls.connect, url=launch_url)
            except Exception as e:
                cls._cleanup_server(server_id)
                raise e

        # If blocking is requested, wait for the process
        if block:
            try:
                process.wait()
            except KeyboardInterrupt:
                cls._cleanup_server(server_id)
                raise
            finally:
                cls._cleanup_server(server_id)

        return connection_manager

    @property
    def endpoints(self) -> list[str]:
        """Return the available commands for the service."""
        return list(self._endpoints)

    @property
    def status(self) -> ServerStatus:
        """Returns the current status of this service."""
        return self._status

    def heartbeat(self) -> Heartbeat:
        """Request the server to do a complete heartbeat check."""
        return Heartbeat(
            status=self.status,
            server_id=self.id,
            message="Heartbeat check successful.",
            details=None,
        )

    @classmethod
    def _cleanup_server(cls, server_id: UUID):
        if server_id in cls._active_servers:
            process = cls._active_servers[server_id]
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                cls.logger.debug(f"Shutting down {server_id} using process {parent} and children processes {children}.")
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                try:
                    parent.terminate()
                    parent.wait(timeout=5)
                except psutil.NoSuchProcess:
                    pass
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                cls.logger.debug("Process already terminated.")
            finally:
                del cls._active_servers[server_id]

    @classmethod
    def _cleanup_all_servers(cls):
        """Cleanup the servers."""
        for server_id in list(cls._active_servers.keys()):
            cls._cleanup_server(server_id)

    @staticmethod
    def shutdown() -> fastapi.Response:
        """HTTP endpoint to shut down the server."""
        os.kill(os.getppid(), signal.SIGTERM)  # kill the parent gunicorn process as it will respawn us otherwise
        os.kill(os.getpid(), signal.SIGTERM)  # kill ourselves as well
        return fastapi.Response(status_code=200, content="Server shutting down...")

    async def shutdown_cleanup(self):
        """Cleanup the server.

        Override this method in subclasses to shut down any additional resources (e.g. db connections) as necessary."""
        try:
            self.logger.debug(f"Successfully released resources for Server {self.id}.")
        except Exception as e:
            self.logger.warning(f"Server did not shut down properly: {e}")

    @classmethod
    def default_url(cls) -> Url:
        """Get the default URL for this server type from config.

        Priority:

        1. Server-specific URL from config
        2. Default ServerBase URL from config
        3. Fallback to localhost:8000
        """
        return parse_url("http://localhost:8080/")

    @classmethod
    def build_url(cls, url: str | Url | None = None, host: str | None = None, port: int | None = None) -> Url:
        """Build a URL with consistent priority logic.

        Priority:

        1. Explicit URL parameter
        2. Host/port parameters
        3. Default URL from config

        Args:
            url: Full URL string or Url object
            host: Host address (e.g. "localhost" or "192.168.1.100")
            port: Port number

        Returns:
            Parsed URL object
        """
        if url is not None:
            if isinstance(url, str):
                url = url + "/" if not url.endswith("/") else url
            return parse_url(url) if isinstance(url, str) else url

        if host is not None or port is not None:
            default_url = cls.default_url()
            final_host = host or default_url.host
            final_port = port or default_url.port
            return parse_url(f"http://{final_host}:{final_port}/")

        return cls.default_url()

    @classmethod
    def register_connection_manager(cls, connection_manager: Type[ConnectionManagerBase]):
        """Register a connection manager for this server."""
        cls._client_interface = connection_manager

    @classmethod
    def default_log_file(cls) -> str:
        """Get the default log file for this server type."""
        return os.path.join(cls.config["DIR_PATHS"]["LOGS"], f"{cls.__name__}_logs.txt")

    def add_endpoint(self, path, func, api_route_kwargs=None, autolog_kwargs=None, methods: list[str] | None = None):
        """Register a new endpoint."""
        path = path.removeprefix("/")
        api_route_kwargs = ifnone(api_route_kwargs, default={})
        autolog_kwargs = ifnone(autolog_kwargs, default={})
        self._endpoints.append(path)
        self.app.add_api_route(
            "/" + path,
            endpoint=autolog(self=self, **autolog_kwargs)(func),
            methods=ifnone(methods, default=["POST"]),
            **api_route_kwargs,
        )
