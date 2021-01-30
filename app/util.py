from flask import jsonify
from sqlalchemy.ext.declarative import DeclarativeMeta

import datetime
import json


DATE_FMT = '%Y-%m-%d'


class ModelEncoder(json.JSONEncoder):
    def val_to_string(self, val):
        if type(val) == datetime.date:
            return val.strftime(DATE_FMT)
        return val

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # go through each field in this SQLalchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata' and not x.startswith('query') and x not in obj.__class__._to_exclude]:
                val = obj.__getattribute__(field)

                # is this field another SQLalchemy object, or a list of SQLalchemy objects?
                if isinstance(val.__class__, DeclarativeMeta) or (isinstance(val, list) and len(val) > 0 and isinstance(val[0].__class__, DeclarativeMeta)):
                    # unless we're expanding this field, stop here
                    if field not in obj.__class__._to_expand:
                        # not expanding this field: set it to None and continue
                        fields[field] = None
                        continue
                fields[field] = self.val_to_string(val)
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)


def to_json(model):
    return json.dumps(model, cls=ModelEncoder)
