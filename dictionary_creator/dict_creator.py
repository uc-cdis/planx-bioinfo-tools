import argparse

def parseOptions():

    parser = argparse.ArgumentParser(description="Introduce variables and nodes files to generate dictionary schemas")
    parser.add_argument("--variables", required=true, help="TSV with variables to include in the dictionary")
    parser.add_argument("--nodes", required=true, help="TSV with ndes to include in the dictionary")    
    parser.add_argument("--schema", default="yaml_template.yaml", help="Template with the schema to create the node YAML") 
    parser.add_argument("--output_path", default="./", help="Path to the output directory") 

    args = parser.parse_args()

    return args

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
					dictionary[h] = columns[pos]
					pos += 1

				if '<node>' in dictionary:
					node = dictionary['<node>']
				else:
					node = dictionary['node']

				rows.setdefault(node, [])
				rows[node].append(dictionary)

    return rows


def createSchemas(args):

	nodes = read_tsv(args.nodes)
	variables = read_tsv(args.variables)

	for node in nodes:

		# Read schema template
		with open(args.schema, 'r') as schemaFile:
			content = schemaFile.read()

		# Fill node properties in schema
		for prop in nodes[node][0]:
			content = content.replace(prop, nodes[node][0][prop])

		# Write output
		outFile = args.output_path + node + '.yaml'
		with open(outFile, 'w') as output:
			output.write(content)

			# Write requirements in schema
			output.write('\n')
			output.write('  - %s\n' % nodes[node][0]['<link_name>'])
			for v in variables[node]:
				if v['required'] == 'Yes':
					output.write('  - %s\n' % v['variable'])

			# Write variables in schema
			output.write('\n')
			output.write('properties:\n')
			output.write('  $ref: "_definitions.yaml#/ubiquitous_properties"\n')
			for v in variables[node]:
				output.write('\n')
				output.write('  %s:\n' % v['variable'])
				output.write('    description: >\n')
				output.write('      %s\n' % v['description'])
				if v['type'] == 'enum':
					output.write('    enum:\n')
					options = v['options'].split('|')
					for op in options:
						output.write('      - "%s"\n' % op)
				else:
					output.write('    type: %s\n' % v['type'])

			output.write('\n')
			output.write('  %s:\n' % nodes[node][0]['<link_name>'])
			if 'to_one' in nodes[node][0]['<multiplicity>']:
				output.write('    $ref: "_definitions.yaml#/to_one"\n')
			else:
				output.write('    $ref: "_definitions.yaml#/to_many"\n')

if __name__ == "__main__":

    args = parseOptions()

    createSchemas(args)



