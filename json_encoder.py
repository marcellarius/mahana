import datetime
import json
import decimal


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, datetime.date):
            return datetime.datetime(o.year, o.month, o.day).isoformat()
        elif isinstance(o, decimal.Decimal):
        	return str(o)
        else:
        	return json.JSONEncoder.default(self, o)
