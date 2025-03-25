import requests

from mindtrace.services import ConnectionManagerBase, ProxyConnectionManager


class GatewayConnectionManager(ConnectionManagerBase):
    """The GatewayConnectionManager class provides a set of methods to interact with the Gateway service."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registered_apps = {}

    @property
    def registered_apps(self):
        return list(self._registered_apps)

    def register_app(self, name: str, url: str, connection_manager: ConnectionManagerBase | None = None):
        """Wrapper method to register an app to the gateway.

        If the optional connection manager argument is passed in, it will be exposed through gateway connection manager
        as its own attribute with the passed in argument name. Refer to the sample below for example usage.

        Parameters:
            name: The name of the app to register.
            url: The app's exposed URL.
            connection_manager: A ConnectionManagerBase instance for the registered app.

        Example::

            import requests
            from mindtrace.services import Gateway, ServerBase

            routed_service_url = "http://localhost:8080/"
            gateway_url = "http://localhost:8081/"

            routed_service = ServerBase.launch(url=routed_service_url)
            gateway = Gateway.launch(url=gateway_url)
            gateway.register_app(name="registered_service", url=routed_service_url, connection_manager=routed_service)

            # The name argument becomes the path route for the gateway:
            requests.get(routed_service_url + "status").json()  # {'status': 'Available'}
            requests.get(gateway_url + "registered_service/status").json()  # Routes the same request through the gateway

            # The registered connection manager is also directly accessible through its gateway counterpart:
            routed_service.status  # <ServerStatus.Available: 'Available'>
            gateway.registered_service.status  # Routes the request
        """
        payload = {"name": name, "url": url}
        response = requests.request("POST", str(self.url) + "register_app", json=payload, timeout=60)
        if response.status_code == 200:
            if connection_manager:
                # Create a proxy connection manager to reroute requests through the gateway
                proxy_cm = ProxyConnectionManager(gateway_url=self.url, app_name=name, original_cm=connection_manager)
                self._registered_apps[name] = proxy_cm
                setattr(self, name, proxy_cm)

        return response.json()
