import json

from sheets import *

sheet = Sheet(
    source=[[i, 'test'] for i in range(10)],
    fields=[
        Field('index', 0, int, None, 'Index'),
        Field('test', 1, str, None, 'Test'),
    ],
)

print(json.dumps(sheet.to_dict(), indent=4))
