import coreapi
from coreapi.exceptions import ErrorMessage


class API:
    def __init__(self):
        self.client = coreapi.Client()
        self.document = self.client.get("http://127.0.0.1:8000/api/schema")

    def action(self, *keys, params, action=None):
        try:
            return self.client.action(self.document, keys, params=params, action=action)
        except ErrorMessage as e:
            keys = "/".join(keys)
            print(f"API Error: {e}, {keys}, params: {params}")
        return {}


api = API()


def patch_coreapi():
    """
    coreapi自带的这个函数会导致如果path和data里有相同的参数，其中一个会被丢弃，并可能导致错误。
    本补丁确保出现在不同位置的参数都能正确发挥作用。
    """
    from collections import defaultdict
    import coreapi.transports.http
    from coreapi.transports.http import Params
    from coreapi.utils import guess_filename, is_file
    from coreapi import exceptions, utils

    def _get_params(method, encoding, fields, params=None):
        """
        Separate the params into the various types.
        """
        if params is None:
            return empty_params

        # field_map = {field.name: field for field in fields}
        field_map = defaultdict(list)
        for field in fields:
            field_map[field.name].append(field)

        path = {}
        query = {}
        data = {}
        files = {}

        errors = {}

        # Ensure graceful behavior in edge-case where both location='body' and
        # location='form' fields are present.
        seen_body = False

        for key, value in params.items():
            fields = field_map.get(key, [None])
            for field in fields:
                if not field:
                    location = 'query' if method in ('GET', 'DELETE') else 'form'
                else:
                    location = field.location

                if location == 'form' and encoding == 'application/octet-stream':
                    # Raw uploads should always use 'body', not 'form'.
                    location = 'body'

                try:
                    if location == 'path':
                        path[key] = utils.validate_path_param(value)
                    elif location == 'query':
                        query[key] = utils.validate_query_param(value)
                    elif location == 'body':
                        data = utils.validate_body_param(value, encoding=encoding)
                        seen_body = True
                    elif location == 'form':
                        if not seen_body:
                            data[key] = utils.validate_form_param(value, encoding=encoding)
                except exceptions.ParameterError as exc:
                    errors[key] = "%s" % exc

        if errors:
            raise exceptions.ParameterError(errors)

        # Move any files from 'data' into 'files'.
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if is_file(data[key]):
                    files[key] = data.pop(key)

        return Params(path, query, data, files)

    coreapi.transports.http._get_params = _get_params

patch_coreapi()
