import os
import string
import random
import requests
import xml.etree.ElementTree as ET
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
ocl_url = os.getenv('OCL_URL')
ocl_token = os.getenv('OCL_TOKEN')
ocl_namespace = os.getenv('OCL_NAMESPACE')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/process_ticket', methods=['GET', 'POST'])
def process_ticket():
    next = request.values.get('next', '')
    if request.method == 'POST':
        namespace = ocl_namespace if ocl_namespace else '' #set default here
        url = ocl_url if ocl_url else '' #set default here
        access_token = ocl_token if ocl_token else '' #set default here
        
        # login
        ocl_response = os.system(f'oc login {url} --insecure-skip-tls-verify=true --token {access_token}')

        # secret
        secret_name = 'sbr-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
        secret_response = os.system(f'oc create secret --namespace {namespace} generic {secret_name} \
            --from-literal=password={request.form.get("password")} \
            --from-literal=username={request.form.get("username")}\
            --from-literal=ticket={str(request.form.get("ticket"))}\
            --from-literal=server={str(request.form.get("server"))}\
            --type=kubernetes.io/basic-auth')

        job_name = 'sbr-job-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
        job_response = os.system(f'oc new-app --namespace {namespace} --template={namespace}/sbr-newjob -p SBRSECRET={secret_name} -p SBEJOBNAME={job_name}')

        status_check = ['1', 'Running']
        if not job_response:
            while status_check[1] == 'Running' and status_check[0] == '1':
                job_status = os.popen('oc describe job sbr').read()
                job = job_status.split('\n')
                status = list
                for param in job:
                    if ':' in param:
                        key, val = param.split(':', 1)
                        if key == 'Pods Statuses':
                            status = [stat.strip().split(' ') for stat in val.split('/')]
                            break
                solution = ""
                url = f'https://access.redhat.com/support/cases/#/case/{str(request.form.get("ticket"))}'
                if status:
                    for stat in status:
                        status_check = stat
                        print('status_check', status_check)
                        if stat[1] == 'Running' and stat[0] == '1':
                            break
                        elif stat[1] == 'Succeeded' and stat[0] == '1':
                            success = True
                            comment_url = f'https://api.access.redhat.com/rs/cases/{str(request.form.get("ticket"))}/comments'
                            response = requests.get(comment_url, auth=(request.form.get("username"), request.form.get("password")))
                            if response.status_code == 200:
                                xml = response.text
                                tree = ET.fromstring(xml)
                                try:
                                    solution = tree[1][4].text
                                    print(solution.split('\n'))
                                except:
                                    pass
                            break
                        else:
                            success = False
                else:
                    success = False

    return render_template('end.html', success=success, ticket=str(request.form.get("ticket")), url=url, solution=solution)


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
