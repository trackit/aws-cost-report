import collections
import random
import itertools

Field = collections.namedtuple('Field', ['name', 'index', 'type', 'group', 'pretty'])
FieldGroup = collections.namedtuple('FieldGroup', ['name', 'pretty'])
Formula = collections.namedtuple('Formula', ['value'])

class Sheet:
    _HEADER_ROW = 0
    _HEADER_COL = 0
    _BODY_ROW = 2
    _BODY_COL = 0

    _CELL_TYPES = collections.defaultdict(lambda: 'stringValue', {
        int: 'numberValue',
        float: 'numberValue',
        bool: 'boolValue',
        Formula: 'formulaValue',
    })

    def __init__(self, source, fields, field_groups=[], sheet_id=None):
        assert all(any(group.name == field.group for group in field_groups) for field in fields if field.group is not None)
        self._source = source
        self._fields = [
            f._replace(group=next(g for g in field_groups if g.name == f.group)) if f.group is not None else f
            for f in fields
        ]
        self._field_groups = field_groups
        self._sheet_id = sheet_id or random.randint(0, 2**32)
        self.properties = {}
        self._row_count = None

    def to_dict(self):
        return {
            'properties': self._to_dict_properties(),
            'data': self._to_dict_data(),
            'merges': self._to_dict_merges(),
        }

    def field_index(self, field, row_num):
        if isinstance(field, basestring):
            field = next(f for f in self._fields if f.name == field)
        col_num = self._fields.index(field)
        row_num = row_num
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
        row_data = [
            {
                'values': [
                    {
                        'userEnteredValue': {
                            'stringValue': f.group.pretty if f.group is not None else f.pretty
                        },
                    }
                    for f in self._fields
                ]
            },
            {
                'values': [
                    {
                        'userEnteredValue': {
                            'stringValue': f.pretty
                        },
                    }
                    for f in self._fields
                ]
            }
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
                    {
                        'userEnteredValue': {
                            cell_type: cell_value,
                        },
                    }
                    for cell_type, cell_value in (self._cell_contents(row, field, row_num, col_num) for field, col_num in zip(self._fields, itertools.count()))
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

    def _merge_group(self, group, fields):
        if group is not None:
            return ({
                'startColumnIndex': fields[0][0] + self._HEADER_COL,
                'endColumnIndex': fields[0][0] + len(fields) + self._HEADER_COL,
                'startRowIndex': 0 + self._HEADER_ROW,
                'endRowIndex': 1 + self._HEADER_ROW,
                'sheetId': self._sheet_id,
            },)
        else:
            return (
                {
                    'startColumnIndex': index + self._HEADER_COL,
                    'endColumnIndex': index + 1 + self._HEADER_COL,
                    'startRowIndex': 0 + self._HEADER_ROW,
                    'endRowIndex': 2 + self._HEADER_ROW,
                    'sheetId': self._sheet_id,
                }
                for index, _ in fields
            )

    def _to_dict_merges(self):
        return list(itertools.chain.from_iterable(
            self._merge_group(k, list(g))
            for k, g in itertools.groupby(zip(itertools.count(), self._fields), key=lambda f: f[1].group)
        ))
