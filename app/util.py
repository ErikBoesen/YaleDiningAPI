from sqlalchemy.ext.declarative import DeclarativeMeta
import json
from flask import jsonify


class ModelEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # a SQLAlchemy model
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data) # this will fail on non-encodable values, like other classes
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

def to_json(model, run_jsonify=False):
    if isinstance(model, list):
        out = [to_json(m, run_jsonify=False) for m in model]
    else:
        out = json.dumps(model, cls=ModelEncoder)
    if run_jsonify:
        out = jsonify(out)
    return out
