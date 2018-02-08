import collections
import random
import itertools
import functools
from singledispatch import singledispatch

Field = collections.namedtuple('Field', ['name', 'index', 'type', 'pretty', 'format'])
FieldGroup = collections.namedtuple('FieldGroup', ['pretty', 'children'])
FieldRoot = collections.namedtuple('FieldRoot', ['children'])
Formula = collections.namedtuple('Formula', ['value'])
ConditionalFormat = collections.namedtuple('ConditionalFormat', ['type', 'value', 'format'])
ColumnConditionalFormat = collections.namedtuple('ColumnConditionalFormat', ['field', 'formats'])

@singledispatch
def _field_depth(arg):
    raise ValueError("arg must be Field or FieldGroup, is {}".format(type(arg)))

@_field_depth.register(Field)
def _(_):
    return 1

@_field_depth.register(FieldGroup)
def _(field_group):
    return 1 + max(_field_depth(f) for f in field_group.children)

@_field_depth.register(FieldRoot)
def _(field_root):
    return max(_field_depth(f) for f in field_root.children)

@singledispatch
def _field_width(arg):
    raise ValueError("arg must be Field or FieldGroup")

@_field_width.register(Field)
def _(_):
    return 1

@_field_width.register(FieldGroup)
@_field_width.register(FieldRoot)
def _(field_group):
    return sum(_field_width(f) for f in field_group.children)

@singledispatch
def _field_slice(arg, row_num):
    raise ValueError("arg must be Field or FieldGroup, is {}".format(type(arg)))

@_field_slice.register(Field)
def _(field, _):
    return [field]

@_field_slice.register(FieldGroup)
def _(field_group, row_num):
    if row_num == 0:
        return [field_group]
    else:
        return sum((_field_slice(f, row_num - 1) for f in field_group.children), [])

@singledispatch
def field_flatten(arg):
    raise ValueError("arg is {}".format(type(arg)))

@field_flatten.register(FieldRoot)
@field_flatten.register(FieldGroup)
def _(field_group):
    return itertools.chain.from_iterable(
        field_flatten(c) for c in field_group.children
    )

@field_flatten.register(Field)
def _(field):
    return (field,)

@_field_slice.register(FieldRoot)
def _(field_root, row_num):
    return sum((_field_slice(f, row_num) for f in field_root.children), [])

@singledispatch
def _field_find(arg, f):
    raise ValueError("arg must be Field or FieldGroup")

@_field_find.register(Field)
def _(field, f):
    if f == field or isinstance(f, basestring) and f == field.name:
        return field
    else:
        return None

@_field_find.register(FieldGroup)
@_field_find.register(FieldRoot)
def _(field_group, f):
    return reduce(
        lambda a, b: a or b,
        (_field_find(e) for e in field_group.children),
    )

@singledispatch
def _field_index(arg, f, o):
    raise ValueError("arg must be Field or FieldGroup")

@_field_index.register(Field)
def _(field, f, o):
    if f == field or isinstance(f, basestring) and f == field.name:
        return o
    else:
        return None

@_field_index.register(FieldGroup)
@_field_index.register(FieldRoot)
def _(field_group, f, o):
    for c in field_group.children:
        r = _field_index(c, f, o)
        if r == None:
            o += _field_width(c)
        else:
            return r
    return None

@singledispatch
def _field_flatten(arg, f, o):
    raise ValueError("arg must be Field or FieldGroup")

@_field_flatten.register(Field)
def _(field):
    return (field,)

@_field_flatten.register(FieldGroup)
@_field_flatten.register(FieldRoot)
def _(field_group):
    return itertools.chain.from_iterable(
        _field_flatten(f) for f in field_group.children
    )

def _add_dict(a, b):
    a = a.copy()
    a.update(b)
    return a

class Sheet:

    _CELL_TYPES = collections.defaultdict(lambda: 'stringValue', {
        int: 'numberValue',
        float: 'numberValue',
        bool: 'boolValue',
        Formula: 'formulaValue',
    })

    def __init__(self, source, fields, fields_conditional_formats=(), sheet_id=None):
        self._source = source
        self._fields = FieldRoot(fields)
        self._sheet_id = sheet_id or random.randint(0, 2**32)
        self.properties = {}
        self._fields_conditional_formats = fields_conditional_formats
        self._row_count = None
        self._HEADER_ROW = 0
        self._HEADER_COL = 0
        self._BODY_ROW = _field_depth(self._fields)
        self._BODY_COL = 0

    def to_dict(self):
        return {
            'properties': self._to_dict_properties(),
            'data': self._to_dict_data(),
            'merges': self._to_dict_merges(),
            'conditionalFormats': self._to_dict_conditional_formats(),
        }

    def field_index(self, field, row_num=None):
        col_num = _field_index(self._fields, field, 0)
        if row_num is None:
            return col_num
        else:
            return col_num, row_num

    def field_address(self, field, row_num, absolute=0):
        col_num, row_num = self.field_index(field, row_num)
        return self.address(col_num, row_num, absolute)

    def address(self, col_num, row_num, absolute=0):
        return ''.join([
            '$' if absolute & 2 else '',
            self.col_address(col_num),
            '$' if absolute & 1 else '',
            self.row_address(row_num),
        ])

    def row_address(self, row_number):
        return str(row_number + 1 + self._BODY_ROW)
        
    def col_address(self, col_number):
        res = []
        n = col_number + self._BODY_COL
        while n >= 0:
            nc = n % 26 + 65
            res.append(nc)
            n = n // 26 - 1
        return ''.join(map(chr, res))

    def _cell_contents(self, row, field, row_num, col_num):
        if field.type in (str, int, float):
            if row[field.index] == '':
                return Sheet._CELL_TYPES[field.type], field.type()
            else:
                return Sheet._CELL_TYPES[field.type], field.type(row[field.index])
        elif callable(field.type):
            value = field.type(self, row_num, col_num, field)
            cell_type = Sheet._CELL_TYPES[type(value)]
            if type(value) == Formula:
                value = value.value
            return cell_type, value

    def _column_range(self, field):
        col_start = self.field_index(field) + self._BODY_COL
        row_start = self._BODY_ROW
        col_end   = col_start + 1
        row_end   = row_start + self._row_count
        return {
            'startColumnIndex': col_start,
            'endColumnIndex': col_end,
            'startRowIndex': row_start,
            'endRowIndex': row_end,
            'sheetId': self._sheet_id,
        }

    def _to_dict_conditional_formats(self):
        return [
            {
                'ranges': self._column_range(column_format.field),
                'booleanRule': {
                    'condition': {
                        'type': format.type,
                        'values': [
                            {
                                'userEnteredValue': format.value,
                            },
                        ],
                    },
                    'format': format.format
                }
            }
            for column_format in self._fields_conditional_formats
            for format in column_format.formats
        ]

    def _to_dict_properties(self):
        res = self.properties.copy()
        res.update({
            'sheetId': self._sheet_id,
        })
        return res

    def _to_dict_data(self):
        return [
            self._to_dict_data_header(),
            self._to_dict_data_body(),
        ]

    def _to_dict_data_header(self):
        header_height = _field_depth(self._fields)
        row_data = [
            {
                'values': sum((
                        [
                            {
                                'userEnteredValue': {
                                    'stringValue': f.pretty
                                },
                                'userEnteredFormat': {
                                    'horizontalAlignment': 'center',
                                    'verticalAlignment': 'middle',
                                    'textFormat': {
                                        'bold': True,
                                        'fontSize': 10 if header_row == 0 else 8,
                                    },
                                },
                            }
                        ] * _field_width(f)
                        for f in header_slice
                    ), []
                )
            }
            for header_slice, header_row in ((_field_slice(self._fields, h), h) for h in range(header_height))
        ]
        return {
            'startRow': self._HEADER_ROW,
            'startColumn': self._HEADER_COL,
            'rowData': row_data,
        }

    def _to_dict_data_body(self):
        row_data = [
            {
                'values': [
                    _add_dict({
                        'userEnteredValue': {
                            cell_type: cell_value,
                        },
                    }, {
                        'userEnteredFormat': {
                            'numberFormat': {
                                'type': 'NUMBER',
                                'pattern': field.format,
                            },
                        },
                    })
                    for cell_type, cell_value, field in (
                        self._cell_contents(row, field, row_num, col_num) + (field,)
                        for field, col_num in zip(_field_flatten(self._fields), itertools.count())
                    )
                ],
            }
            for row, row_num in zip(self._source, itertools.count())
        ]
        self._row_count = len(row_data)
        return {
            'startRow': self._BODY_ROW,
            'startColumn': self._BODY_COL,
            'rowData': row_data,
        }

    def _to_dict_merges(self):
        merges = []
        seen_fields = set()
        for header_row in range(_field_depth(self._fields)):
            header_slice = _field_slice(self._fields, header_row)
            col_start = 0
            for header in header_slice:
                if type(header) == FieldGroup:
                    col_width = _field_width(header)
                    merges.append({
                        'startColumnIndex': col_start + self._HEADER_COL,
                        'endColumnIndex': col_start + col_width + self._HEADER_COL,
                        'startRowIndex': header_row + self._HEADER_ROW,
                        'endRowIndex': header_row + 1 + self._HEADER_ROW,
                        'sheetId': self._sheet_id,
                    })
                    col_start += col_width
                elif type(header) == Field and header not in seen_fields:
                    col_width = 1
                    merges.append({
                        'startColumnIndex': col_start + self._HEADER_COL,
                        'endColumnIndex': col_start + col_width + self._HEADER_COL,
                        'startRowIndex': header_row + self._HEADER_ROW,
                        'endRowIndex': self._BODY_ROW,
                        'sheetId': self._sheet_id,
                    })
                    col_start += col_width
                    seen_fields.add(header)
                else:
                    col_start += 1
        return merges

test_fields = FieldRoot((
    Field('first', 0, int, 'First', None),
    Field('second', 0, int, 'Second', None),
    FieldGroup('Grouped', (
        Field('third', 0, int, 'Third', None),
        Field('fourth', 0, int, 'Fourth', None),
        FieldGroup('Nested', (
            Field('fifth', 0, int, 'Fifth', None),
            Field('sixth', 0, int, 'Sixth', None),
        )),
    )),
    Field('seventh', 0, int, 'Seventh', None),
    Field('eighth', 0, int, 'Eigth', None),
))

var_fields = FieldRoot((
	Field(name='usage', index='usage', type=str, pretty='Usage type', format=None),
	FieldGroup(pretty='Monthly cost', children=(
		FieldGroup(pretty='2017-10', children=(
			Field(name='cost2017-10', index='2017-10', type=float, pretty='Cost', format='#,##0.000 [$USD]'),
		)),
		FieldGroup(pretty='2017-11', children=(
			Field(name='cost2017-11', index='2017-11', type=float, pretty='Cost', format='#,##0.000 [$USD]'),
			Field(name='var2017-11', index='2017-11', type=float, pretty='Variation', format='0.00%')
		)),
		FieldGroup(pretty='2017-12', children=(
			Field(name='cost2017-12', index='2017-12', type=float, pretty='Cost', format='#,##0.000 [$USD]'),
			Field(name='var2017-12', index='2017-12', type=float, pretty='Variation', format='0.00%')
		)),
		FieldGroup(pretty='2018-01', children=(
			Field(name='cost2018-01', index='2018-01', type=float, pretty='Cost', format='#,##0.000 [$USD]'),
			Field(name='var2018-01', index='2018-01', type=float, pretty='Variation', format='0.00%')
		)),
		FieldGroup(pretty='2018-02', children=(
			Field(name='cost2018-02', index='2018-02', type=float, pretty='Cost', format='#,##0.000 [$USD]'),
			Field(name='var2018-02', index='2018-02', type=float, pretty='Variation', format='0.00%')
		))
	))
))
