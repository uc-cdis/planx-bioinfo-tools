import json
import os
import yaml
from shutil import rmtree
from copy import deepcopy

print '\n\n'

schemas_path = '../ndhdictionary/gdcdictionary/schemas/'

prop_defs = yaml.load(open(schemas_path + '_definitions.yaml'))
term_defs = yaml.load(open(schemas_path + '_terms.yaml'))

ignore_schemas = ['_definitions.yaml', '_terms.yaml', '_settings.yaml', 'projects', 'README.md', 'project.yaml']

schema_files = os.listdir(schemas_path)

if os.path.exists('../report_files'):
    rmtree('../report_files')

os.mkdir('../report_files')

header = 'Node\tProperty\tType\tEnum_Values\tDescription\tFlags\n'

master_out_file = open('../report_files/_master_summary.tsv', 'w')
master_out_file.write(header)

for schema_file in schema_files:

    if schema_file not in ignore_schemas:
        print '----- ' + schema_file[:-5] + ' -----'

        schema = yaml.load(open(schemas_path + schema_file))

        node_props = schema['properties']

        while '$ref' in node_props:
            prop_path = node_props.pop('$ref').split('/')

            try:
                # all referenced property lists are contained in
                # _definitions.yaml (i.e., ubiquitous_properties, data_file_properties)
                node_props.update(prop_defs[prop_path[1]])
            except:
                print('not in _defintions.yaml - see path:')
                print(prop_path)

        # now node_props contains all properties, with no $ref lists

        results = []

        write_header = True

        for prop in node_props:

            out_dict = {'node': schema_file[:-5],
                        'property': prop,
                        'type': None,
                        'enum_values': None,
                        'description': None,
                        'flags': []}

            collect_flag = False

            prop_block = node_props[prop]

            # if enum with yes/no options present
            if 'enum' in prop_block:
                out_dict['type'] = 'enum'
                enum_list = prop_block['enum']
                out_dict['enum_values'] = enum_list
                for val in enum_list:
                    for word in ['ever', 'yes', 'never','positive','negative']:
                        if word in val.strip().lower():
                            collect_flag = True
                            out_dict['flags'].append(word)
                    if val.strip().lower() in ['no']:
                        collect_flag = True
                        out_dict['flags'].append(word)

            # if type is boolean
            try:
                if ('type' in prop_block) and (prop_block['type'].lower().strip() == 'boolean'):
                    collect_flag = True
                    out_dict['type'] = 'boolean'
                    out_dict['flags'].append('boolean')
            except:
                view_flag = True
                for term in ['type', 'id', 'data', 'year']:
                    if term in prop.lower():
                        view_flag = False

                if view_flag:
                    print 'the property type is a list:'
                    print prop
                    print json.dumps(prop_block, indent=2)


            # other words to indicate boolean type response
            if 'ever' in prop.lower(): # e.g. see follow_up.yaml/properties/ever_transferred
                collect_flag = True
                out_dict['flags'].append('ever')

            desc = ''

            # if yes/no in the description
            if 'description' in prop_block:
                desc = prop_block['description']

            # _terms.yaml#/weight
            elif 'term' in prop_block:
                try:
                    term_path = prop_block['term']['$ref'].split('/')
                    term_name = term_path[1]
                    term_entry = term_defs[term_name]
                    desc = term_entry['description']
                except:
                    print 'term issue: '
                    print prop
                    print json.dumps(prop_block, indent=2)

            # create general dereference function

            # $ref: "_definitions.yaml#/datetime"
            elif '$ref' in prop_block:
                '''
                print 'here is a reference in the the block'
                print prop
                print json.dumps(prop_block, indent=2)
                '''
                # wrap this into a function - dereference definition
                prop_path = prop_block['$ref'].split('/')
                prop_name = prop_path[1]
                prop_entry = prop_defs[prop_name]
                if 'description' in prop_entry:
                    desc = prop_entry['description']
                elif 'term' in prop_entry:
                    # encapsulate this bit into a function - dereference term
                    term_path = prop_entry['term']['$ref'].split('/')
                    term_name = term_path[1]
                    term_entry = term_defs[term_name]
                    desc = term_entry['description']

            else:
                view_flag = True
                for term in ['type', 'id']:
                    if term in prop:
                        view_flag = False

                if view_flag:
                    print 'WARNING : No desc, term or $ref for prop - ' + prop
                    print json.dumps(prop_block, indent=2)

            if desc is None and prop != 'type':
                print '\nWARNING : Could not find a desc for prop - ' + prop

            # words to indicate boolean type response
            # presently excluding 'no' because it is a substring of 'node', among other common enough words, to gather unnecessary output
            for word in ['yes', 'ever ', 'whether','did']:
                if word in desc.lower():
                    collect_flag = True
                    out_dict['flags'].append(word)

            out_dict['description'] = desc.strip().encode('utf-8')

            # by now we should have caught all the issues
            # collect them and write the output - make this as clear, easy to read, and useful information as possible

            if collect_flag is True and out_dict['type'] not in [None, 'boolean']:
                output = (out_dict['node'], out_dict['property'], out_dict['type'], out_dict['enum_values'], out_dict['description'], out_dict['flags'])
                master_out_file.write('%s\t%s\t%s\t%s\t%s\t%s\n' % output)
                with open('../report_files/' + schema_file[:-5] + '.tsv', 'a+') as out_file:
                    if write_header:
                        out_file.write(header)
                        write_header = False
                    out_file.write('%s\t%s\t%s\t%s\t%s\t%s\n' % output)

print '\n\n'
