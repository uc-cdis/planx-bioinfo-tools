# Gen3 submission tools

Collection of Python scripts to manage submissions and deletions in any Gen3 Data Commons using the appropiate API and pagination.

### 1. Submission tool:

This tool (see [submitter.py](submitter.py)) helps to submit large metadata TSVs node by node using pagination. Arguments:

* `-f/--file` TSV file for submission in specific node.
* `-a/--apiurl` URL for data commons where the metadata is submitted. E.g. https://niaid.bionimbus.org
* `-p/--project` Project ID where the metadata is submitted. E.g. ndh-CHARLIE
* `-k/--authfile` JSON file containing the credentials/keys.
* `-l/--length` Length of the chunk to use for paginated submission.
* `-r/--row` Initial row from where to start submission.
* `-o/--output` (OPTIONAL) Output folder to containg output logs (default: `./output/`)

Usage example:

```python
python submitter.py -f case.tsv \
	-a https://niaid.bionimbus.org \
	-p ndh-CHARLIE \
	-k credentials.json \ 
	-l 100 \
	-r 1
```

### 2. Deletion tool:

This tool (see [delete.py](delete.py)) helps to remove a list of entities from the data commons or an entire node. Arguments:

* `-a/--apiurl` URL for data commons where the metadata is submitted. E.g. https://niaid.bionimbus.org
* `-p/--project` Project ID where the metadata is submitted. E.g. ndh-CHARLIE
* `-n/--node` Node from where entities will be removed.
* `-k/--authfile` JSON file containing the credentials/keys.
* `-l/--length` Length of the chunk to use for paginated deletion (default: 20).
* `-e/--nentities` Total number of entities to remove (default: 10000).
* `-f/--file` (OPTIONAL) File with a list of ids (submitter_id) to remove from the selected node.

Usage Example:

```python
python delete.py -a https://niaid.bionimbus.org \
        -p ndh-CHARLIE \
        -n case \
        -k credentials.json \
        -l 20 \
        -e 10000 \
```
