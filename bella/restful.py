import coreapi


class API:
    def __init__(self):
        self.client = coreapi.Client()
        self.document = self.client.get("http://127.0.0.1:8000/api/schema")

    def action(self, *keys, params):
        return self.client.action(self.document, keys, params)


api = API()
