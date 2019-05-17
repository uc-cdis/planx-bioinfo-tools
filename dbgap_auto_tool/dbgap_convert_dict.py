import argparse

used_headers = [
    'Variable',
    'Description',
    'Type',
    'Coded values'
]

out_headers = {
    'Variable': 'Field',
    'Description': 'Description',
    'Type': 'Type',
    'Coded values': 'Options',
    'Codes': 'Codes'
}

type_mapping = {
    "NUMERIC": "number",
    "STRING": "string"
}


def parseOptions():

    parser = argparse.ArgumentParser(description="Convert dbGap dictionary to table")
    parser.add_argument("--dictionary", default=None, help="File containing the data dictionary from dbGap")
    args = parser.parse_args()

    return args


def convert_dict(filename):

    headers = []
    values = {}
    with open(filename, 'r') as dic:
        for line in dic:
            columns = line.strip('\n')
            columns = columns.split('\t')

            if headers == []:
                headers = columns
                outline = ""
                for head in used_headers:
                    outline += '%s\t' % out_headers[head]
                outline += 'Codes'
                print outline

            elif columns[0] != "":
                if values:
                    outline = ""
                    for head in used_headers:
                        outline += '%s\t' % (values[head])
                    if 'Codes' in values:
                        outline += values['Codes']
                    else:
                        outline += '\t'
                    print outline

                values = {}
                for head in used_headers:
                    idx = [i for i, j in enumerate(headers) if j == head][0]

                    if head == 'Coded values' and '=' in columns[idx]:
                        values[head] = columns[idx].split('=')[1]
                        values['Codes'] = columns[idx].split('=')[0]
                        if values[head] == "NO":
                            values['Type'] = "boolean"
                        else:
                            values['Type'] = "enum"
                    else:
                        if head == 'Type' and columns[idx] in type_mapping:
                            values[head] = type_mapping[columns[idx]]
                        else:
                            values[head] = columns[idx]

            else:
                idx = [i for i, j in enumerate(headers) if j == 'Coded values'][0]
                if '=' in columns[idx]:
                    values['Coded values'] += "," + columns[idx].split('=')[1]
                    values['Codes'] += "," + columns[idx].split('=')[0]
                else:
                    values['Coded values'] += "," + columns[idx]


if __name__ == "__main__":

    args = parseOptions()

    convert_dict(args.dictionary)
