import argparse
import json
import os

# make this cleaner, or create another config file and put these things there
all_link_props = ['<link_name>', '<backref>', '<label>', '<target>', '<multiplicity>', '<link_required>', '<link_group_required>', '<group_exclusive>']
single_link_props = ['<link_name>', '<backref>', '<label>', '<target>', '<multiplicity>', '<link_required>']

def parse_options():
    global args

    parser = argparse.ArgumentParser(description="Introduce variables and nodes files to generate dictionary schemas")
    parser.add_argument("-d", "--directory", dest="dir", required=True, help="Directory containing target nodes.tsv and variables.tsv files")

    # parser.add_argument("--separator", default='","', help="Separator used for list of options")

    args = parser.parse_args()

def read_tsv(filename):

    headers = []
    rows = {}
    with open(filename, 'r') as schemaFile:
        for line in schemaFile:
            columns = line.strip('\n').split('\t')
            if not headers:
                headers = columns
            else:
                pos = 0
                dictionary = {}
                # print columns
                for h in headers:
                    try:
                        dictionary[h] = columns[pos]
                        pos += 1
                    except:
                        pass

                if '<node>' in dictionary:
                    node = dictionary['<node>']
                else:
                    node = dictionary['Node']

                # this is a super temporary fix, to fix capitalization issue
                # make a better revision later
                make_lower_case = ['<link_required>', '<link_group_required>', '<group_exclusive>']

                for key in make_lower_case:
                    try:
                        dictionary[key] = dictionary[key].lower()
                    except:
                        pass

                rows.setdefault(node, [])
                rows[node].append(dictionary)

    return rows

def get_data(directory):

    path = '../input_tsv/' + directory + '/'
    nodes_file = path + 'nodes.tsv'
    var_file = path + 'variables.tsv'
    return read_tsv(nodes_file), read_tsv(var_file)

def mkdir(directory):

    if not os.path.exists(directory):
        os.makedirs(directory)

def get_templates():

    # Read schema template
    with open('config/yaml_template.yaml', 'r') as schemaFile:
        content = schemaFile.read()

    # Read link template
    with open('config/link_template.yaml', 'r') as linkFile:
        link = linkFile.read()

    # Read link group template
    with open('config/group_template.yaml', 'r') as groupFile:
        link_group = groupFile.read()

    with open('config/group_link_template.yaml', 'r') as groupLinkFile:
        group_link = groupLinkFile.read()

    return content, link, link_group, group_link

def write_file(node, content):
    # encapsulate a lot of these writing segments into functions
    global nodes, variables, args

    out_file = '../' + args.dir + '_dict/' + node + '.yaml'

    with open(out_file, 'w') as output:
        output.write(content)
        output.write('\n')

        # Write requirements in schema
        link_map = build_link_map(node)

        for i in range(len(link_map['<link_name>'])):
            if type(link_map['<link_name>'][i]) is str:
                link_name = link_map['<link_name>'][i]
                link_req = link_map['<link_required>'][i]

                if link_req.lower() == 'true':
                    output.write('  - %s\n' % link_name)

            else:
                link_group = link_map['<link_name>'][i]
                link_req_group = link_map['<link_required>'][i]

                for k in range(len(link_group)):
                    link_name = link_group[k]
                    if link_req_group[k].lower() == 'true':
                        output.write('  - %s\n' % link_name)

        for v in variables[node]:
            if v['Required'] == 'Yes':
                output.write('  - %s\n' % v['Field'])

        # Write variables in schema
        output.write('\n')
        output.write('properties:\n')
        output.write('  $ref: "_definitions.yaml#/ubiquitous_properties"\n')

        for v in variables[node]:

            # Add description
            output.write('\n')
            output.write('  %s:\n' % v['Field'])
            output.write('    description: >\n')
            output.write('      %s\n' % v['Description'])

            # Add type
            if v['Type'] == 'enum':
                output.write('    enum:\n')
                # Remove initial and final `"` characters if used as separator
                # if '"' in args.separator:
                v['Options'] = v['Options'][1:-1]
                options = v['Options'].split('","')
                for op in options:
                    output.write('      - "%s"\n' % op.strip())

            else:
                output.write('    type: %s\n' % v['Type'])

            # Add ontology term if existing
            if v['Term'] != "":
                output.write('    term:\n')
                output.write('       termDef:\n')
                output.write('          cde_id: %s\n' % v['Term'])

        for i in range(len(link_map['<link_name>'])):
            if type(link_map['<link_name>'][i]) is str:
                link_name = link_map['<link_name>'][i]
                link_mult = link_map['<multiplicity>'][i]
                output.write('\n')
                output.write('  %s:\n' % link_name)
                if 'to_one' in link_mult:
                    output.write('    $ref: "_definitions.yaml#/to_one"\n')
                else:
                    output.write('    $ref: "_definitions.yaml#/to_many"\n')

            else:
                link_group = link_map['<link_name>'][i]
                link_mult_group = link_map['<multiplicity>'][i]

                for k in range(len(link_group)):
                    link_name = link_group[k]
                    link_mult = link_mult_group[k]
                    # a lot of repetition here - encapsulate these bits into functions
                    output.write('\n')
                    output.write('  %s:\n' % link_name)
                    if 'to_one' in link_mult:
                        output.write('    $ref: "_definitions.yaml#/to_one"\n')
                    else:
                        output.write('    $ref: "_definitions.yaml#/to_many"\n')

def parse_entry(input_str):

    if '[' not in input_str:
        out = input_str.split(',')
        return out

    out = []

    temp = input_str.split('[')

    for part in temp:

        if ']' in part:
            group_temp = part.split(']')
            group = group_temp[0]
            entry = group.split(',')
            out.append(entry)

            non_group = group_temp[1]

        else:
            non_group = part

        non_group = non_group.strip(',')
        non_groups = non_group.split(',')
        for one_piece in non_groups:
            if len(one_piece) > 0:
                out.append(one_piece)

    return out

def build_link_map(node):

    link_map = {}

    for i in range(len(all_link_props)):
        prop = all_link_props[i]

        if prop == '<backref>':
            link_map[prop] = nodes[node][0]['<backref>']

        else:
            try:
                input_str = nodes[node][0][prop]

                link_map[prop] = parse_entry(input_str)
            except:
                pass

    return link_map

def build_link(link_map, map_place, link_group=False, group_place=None):

    if link_group:
        out = group_link_template

    else:
        out = link_template

    for link_prop in single_link_props:

        if link_prop == '<backref>':
            link_prop_val = link_map['<backref>']

        else:
            if link_group:
                link_prop_val = link_map[link_prop][map_place][group_place]

            else:
                link_prop_val = link_map[link_prop][map_place]

        out = out.replace(link_prop, link_prop_val)

    return out

def build_link_group(link_map, map_place, group_counter):

    link_group = link_map['<link_name>'][map_place]

    out_block = group_template

    for group_prop in ['<group_exclusive>', '<link_group_required>']:
        try:
            group_prop_val = link_map[group_prop][group_counter]
            out_block = out_block.replace(group_prop, group_prop_val)
        except:
            pass

    group_blocks = []

    for k in range(len(link_group)):
        sub_block = build_link(link_map, map_place, True, k)
        group_blocks.append(sub_block)

    group_block = ''.join(group_blocks)

    out_block = out_block.replace('<subgroup>', group_block)

    return out_block

def return_link_block(node):

    link_map = build_link_map(node)

    blocks = []

    group_counter = 0

    for map_place in range(len(link_map['<link_name>'])):

        if type(link_map['<link_name>'][map_place]) is str:
            out_block = build_link(link_map, map_place)

        elif type(link_map['<link_name>'][map_place]) is list:
            out_block = build_link_group(link_map, map_place, group_counter)
            group_counter += 1

        blocks.append(out_block.strip('\n'))

    blocks.sort(key = lambda b: len(b), reverse=True)

    link_block = '\n'.join(blocks)

    return link_block

def create_node_schema(node):

    content = content_template

    # Get links
    link_block = return_link_block(node)

    # Add links to schema template
    content = content.replace('<link>', ''.join(link_block))

    # Fill node properties in schema
    for prop in nodes[node][0]:
        if prop not in all_link_props:
            content = content.replace(prop, nodes[node][0][prop])

    # Write output
    write_file(node, content)

def create_schemas():
    global content_template, link_template, group_template, group_link_template, nodes, variables, args

    mkdir('../' + args.dir + '_dict')

    nodes, variables = get_data(args.dir)

    content_template, link_template, group_template, group_link_template = get_templates()

    for node in nodes:

        create_node_schema(node)

if __name__ == "__main__":

    parse_options()
    create_schemas()
