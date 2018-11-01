import requests
import json

from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission


# settings
SUBMIT_ENDPOINT = "xxx"
SUBMIT_PROGRAM = 'xxx'
SUBMIT_PROJECT = 'xxx'
CREDS_FILE = 'xxx'
BREAK_IF_ERROR = True
DATA_FOLDER = 'S039-1' # name of the folder containing the JSON files to submit
STEP = 50 # how many items to submit at a time

# setup Gen3 SDK
SDK_AUTH = Gen3Auth(SUBMIT_ENDPOINT, refresh_file=CREDS_FILE)
SDK_SUB = Gen3Submission(SUBMIT_ENDPOINT, SDK_AUTH)

# submit in the dictionary order
order = [
    'study',
    'subject',
    'sample'
]


def submit_json(data_json):
    response = SDK_SUB.submit_node(SUBMIT_PROGRAM, SUBMIT_PROJECT, data_json)
    return json.loads(response)


def delete_node(uuid):
    api_url = "{}/api/v0/submission/{}/{}/entities/{}".format(SUBMIT_ENDPOINT, SUBMIT_PROGRAM, SUBMIT_PROJECT, uuid)
    response = requests.delete(api_url, auth=SDK_AUTH).text
    return response


if __name__== "__main__":

    code = 200
    for node_name in order:
        print('Submitting', node_name)
        invalid = []
        with open('{}/{}.json'.format(DATA_FOLDER, node_name), 'r') as f:
            data = json.load(f)
            i = 0
            while i < len(data):
                # submitting items one by one in case one is not valid
                for item in data[i:i + STEP]:
                    response = submit_json(item)
                    code = response['code']
                    if code != 200:
                        invalid.extend([
                            json.dumps(item, indent=4),
                            json.dumps(response, indent=4),
                            '--------------------------------------'
                        ])
                        if BREAK_IF_ERROR:
                            break
                if code != 200 and BREAK_IF_ERROR:
                    break
                i += STEP
                print('{} / {}'.format(i if i < len(data) else len(data), len(data)))
        if code != 200:
            for inv in invalid:
                print(inv)
            print(len(invalid)/3, 'invalid submissions')
            if BREAK_IF_ERROR:
                break
