#!/usr/bin/env python2
import argparse
import gen3_data

parser = argparse.ArgumentParser(description="Prepare TSVs")
parser.add_argument('-f', '--file_raw', required=True, help="File with values from dbGaP")
parser.add_argument('-m', '--mapping_file', required=True, help="original dictionary mapping to gen3 dictionary file")


def parse_mapping(raw_file, mapping_file):
    gen3_dict = gen3_data.data_dictionary()
    with open(mapping_file, 'r') as map_file:
        header_line = map_file.readline()
        for line in map_file:
            columns = line.strip('\n').split('\t')
            node = columns[5]
            if node != 'NA':
                if node not in gen3_dict.get_data_node_names():
                    gen3_data_node = gen3_data.data_node(node)
                    gen3_dict.set_data_node(gen3_data_node)
                gen3_node = gen3_dict.get_data_from_node(node)
                dbGap_variable = columns[0]
                gen3_variable = columns[6]
                gen3_node.append_mapping(dbGap_variable, gen3_variable)
                if columns[7] != '':
                    gen3_suffix = columns[7]
                    gen3_node.append_suffix(dbGap_variable, gen3_variable, gen3_suffix)
                if columns[4]:
                    gen3_node.append_convertable(True)
                    codes = columns[4].split('|')
                    coded_values = columns[3].split('|')
                    for i in range(len(codes)):
                        gen3_node.set_code_mapping(gen3_variable, (codes[i], coded_values[i]))
                else:
                    gen3_node.append_convertable(False)
            gen3_dict.set_data_node(gen3_node)
    # we need to look through the raw file to find the correct indicies of the variables
    # these indicies will be used for the selecting the correct values to output for the specific variable 
    with open(raw_file, 'r') as raw_file:
        for line in raw_file:
            columns = line.strip('\n').split('\t')
            columns = map(lambda x: x.strip(), columns)
            # if the line is a comment we skip the line
            if columns[0][0] == '#':
                continue
            # we only need the headers from the raw files
            else:
                for node in gen3_dict.get_data_node_names():
                    gen3_data_node = gen3_dict.get_data_from_node(node)
                    for var_mapping in gen3_data_node.mappings:
                        index = [i for i, x in enumerate(columns) if x == var_mapping.keys()[0]]
                        if index:
                            gen3_data_node.append_index(index[0])
                    gen3_dict.set_data_node(gen3_data_node)
                break
    return gen3_dict


def assign_values(raw_file, gen3_data_dict):
    skip_header = True
    with open(raw_file, 'r') as raw_file:
        for line in raw_file:
            columns = line.strip('\n').split('\t')
            if columns[0][0] == '#':
                continue
            elif skip_header:
                skip_header = False
                headers = line.strip()
            else:
                for node in gen3_data_dict.get_data_node_names():
                    values = ''
                    data_node = gen3_data_dict.get_data_from_node(node)
                    for i in range(len(data_node.indicies)):
                        index = data_node.indicies[i]
                        if index < len(columns):
                            if data_node.convertable[i] == True:
                                code = columns[index]
                                if code:
                                    gen3_variable = data_node.mappings[i].values()
                                    gen3_variable = gen3_variable[0]
                                    code = code.strip()
                                    value = data_node.code_mapping[gen3_variable].get(code)[0]
                                else:
                                    value = ''
                            else:
                                value = columns[index]
                        else:
                            value = ''
                        values += str(value) + '\t'
                    if data_node.suffix:
                        for field in data_node.suffix:
                            fieldDict = {field[0]: field[1]}
                            index = data_node.mappings.index(fieldDict)
                            value_list = values.split('\t')
                            value_list[index] += data_node.suffix[field]
                            values = '\t'.join(value_list)
                    data_node.append_value(values)
                    gen3_data_dict.set_data_node(data_node)
    return gen3_data_dict


def write_tables(gen3_data_dict, study_id):
    for node in gen3_data_dict.get_data_node_names():
        data_node = gen3_data_dict.get_data_from_node(node)
        with open('output_{0}.txt'.format(node), 'w') as f:
            headers = ''
            for i in range(len(data_node.mappings)):
                header = data_node.mappings[i].values()
                header = header[0]
                headers += header + '\t'
            headers += 'type' + '\t'
            f.write(headers)
            if str(node) == "case" and study_id != '':
                f.write("studies.submitter_id")
            f.write('\n')
            for i in range(len(data_node.value)):
                f.write(data_node.value[i])
                f.write(str(node))
                if str(node) == 'case' and study_id != '':
                    f.write('\t')
                    f.write(study_id)
                f.write('\n')
        f.close()
    return gen3_data_dict.get_data_node_names()


if __name__ == '__main__':
    args = parser.parse_args()
    gen3_data = parse_mapping()(args.file_raw, args.mapping_file)
    gen3_data = assign_values()(args.file_raw, gen3_data)
    write_tables(gen3_data)
