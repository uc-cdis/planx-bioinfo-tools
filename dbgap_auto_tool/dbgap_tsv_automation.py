#!/usr/bin/env python2
import argparse

parser = argparse.ArgumentParser(description="Prepare TSVs")
parser.add_argument('-f', '--file_raw', required=True, help="File with values from dbGaP")
parser.add_argument('--mapping_file', required=True, help="original dictionary mapping to gen3 dictionary file")
args = parser.parse_args()
# Initiate a dictionary, keys are node names in gen3 data model and values are three dictionary. Keys for the three dictionaries are varialbe_mapping, convertable and code_mapping.


def parse_dictionary_mapping(raw_file, mapping_file):
    skip_header = True
    gen3_data = dict()
    with open(mapping_file, 'r') as map_file:
        for line in map_file:
            if skip_header:
                skip_header = False
            else:
                columns = line.strip('\n').split('\t')
                node = columns[5].strip()
                if node != 'NA':
                    dbGap_variable = columns[0].strip()
                    gen3_variable = columns[6].strip()
                    gen3_data.setdefault(node, {})
                    gen3_data[node].setdefault('variable_mapping', [])
                    gen3_data[node]['variable_mapping'].append({dbGap_variable: gen3_variable})
                    gen3_data[node].setdefault('convertable', [])
                    if columns[4]:
                        gen3_data[node]['convertable'].append(True)
                        gen3_data[node].setdefault('code_mapping', {})
                        gen3_data[node]['code_mapping'].setdefault(gen3_variable, {})
                        codes = columns[4].split('|')
                        coded_value = columns[3].split('|')
                        for i in range(len(codes)):
                            gen3_data[node]['code_mapping'][gen3_variable][codes[i]] = coded_value[i]
                    else:
                        gen3_data[node]['convertable'].append(False)
    with open(raw_file, 'r') as raw_file:
        for line in raw_file:
            columns = line.strip('\n').split('\t')
            columns = map(lambda x: x.strip(), columns)
            if columns[0][0] == '#':
                continue
            else:
                for node in gen3_data.keys():
                    for variable_mapping in gen3_data[node]['variable_mapping']:
                        index = [i for i, x in enumerate(columns) if x == variable_mapping.keys()[0]]
                        if index:
                            index = index[0]
                            gen3_data[node].setdefault('index', [])
                            gen3_data[node]['index'].append(index)
                break
        return gen3_data

# Parse values from raw_file into list: gen3_data[node]['value']. In the raw_file, remove empty lines before running the script


def parse_value(raw_file, gen3_data):
    skip_header = True
    with open(raw_file, 'r') as raw_file:
        for line in raw_file:
            columns = line.strip('\n').split('\t')
            if columns[0][0] == '#':
                continue
            elif skip_header:
                skip_header = False
            else:
                for node in gen3_data.keys():
                    print(node)
                    values = ''
                    if 'index' in gen3_data[node].keys():
                        for i in range(len(gen3_data[node]['index'])):
                            index = gen3_data[node]['index'][i]
                            if index < len(columns):
                                if gen3_data[node]['convertable'][i] == True:
                                    code = columns[index]
                                    if code:
                                        gen3_variable = gen3_data[node]['variable_mapping'][i].values()
                                        gen3_variable = gen3_variable[0]
                                        code = code.strip()
                                        value = gen3_data[node]['code_mapping'][gen3_variable].get(code)
                                    else:
                                        value = ""
                                else:
                                    value = columns[index]
                            else:
                                value = ""
                            values = values + value + '\t'
                    gen3_data[node].setdefault('value', [])
                    gen3_data[node]['value'].append(values)
        return gen3_data

# Output variable name and values per sample for each node


def output_table(gen3_data):
    for node in gen3_data.keys():
        with open("output_{0}.txt".format(node), 'w') as f:
            headers = ''
            for i in range(len(gen3_data[node]['variable_mapping'])):
                header = gen3_data[node]['variable_mapping'][i].values()
                header = header[0]
                headers = headers + header + '\t'
            f.write(headers)
            f.write("\n")
            for i in range(len(gen3_data[node]['value'])):
                f.write(gen3_data[node]['value'][i])
                f.write("\n")
        f.close()


if __name__ == '__main__':
    gen3_data = parse_dictionary_mapping(args.file_raw, args.mapping_file)
    gen3_data = parse_value(args.file_raw, gen3_data)
    output_table(gen3_data)
