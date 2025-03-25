import json
import requests

from pydantic import BaseModel

from mindtrace.services import Service, ConnectionManagerBase, register_connection_manager


class AddInput(BaseModel):
    x: int
    y: int


class MultiplyInput(BaseModel):
    x: int
    y: int


class MathConnectionManager(ConnectionManagerBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def add(self, x: int, y: int):
        response = requests.post(str(self.url) + "add", json={"x": x, "y": y}, timeout=60)
        return json.loads(response.content)["result"]

    def multiply(self, x: int, y: int):
        response = requests.post(str(self.url) + "multiply", json={"x": x, "y": y}, timeout=60)
        return json.loads(response.content)["result"]


@register_connection_manager(MathConnectionManager)
class MathService(Service):
    def __init__(self, **_):
        super().__init__()
        self.add_endpoint(path="/add", func=self.add)
        self.add_endpoint(path="/multiply", func=self.multiply)

    def add(self, payload: AddInput):
        return {"result": payload.x + payload.y}

    def multiply(self, payload: MultiplyInput):
        return {"result": payload.x * payload.y}
