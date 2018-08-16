# SBR OpenStack Supporter Bot Project

The SBR OpenStack Supppoter bot project is sponsered by **Red Hat Inc**. As a part of **Red Hat** AICoE under Team thoth this project was completed as the Summer Internship project.</br>
The application was developed for **Red Hat** SBR OpenStack Support Team as a POC project.The application serves as automation for the Customer Case Ticket Processing for providing the Customer cases with first assitance.</br>
Once a Ticket has been raised for an Customer Case with attachments , the application can process the ticket and provide first assistance by publishing the probable solution for the Customer Case. 

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live OpenShift Cluster.

### Prerequisites

- Requriments for running and testing the application:

	```
	- User has to have **Red Hat** RHN account.
	- Idap permissions as support or devel to users account.
	- Access to **Red Hat** VPN.
	- OpenShift account to deploy the application.
	```

- Softwares required for development and deployment:
	- Python [Installation Guide](https://www.python.org/)
	- Docker [Installation Guide](https://docs.docker.com/install/)
	- Ansible [Installation Guide](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
	- OpenShift cli [Installation Guide](https://docs.openshift.com/enterprise/3.1/cli_reference/get_started_cli.html#installing-the-cli)

## About the Application

The application (SBR OpenStack Supporter Bot) serves as automation for the customer case ticket processing, it process the ticket by performing following actions:
- Fetching relevant information (attachments,SOS Reports).
- Extracting the SOS Report from the attachment based upon the SOS Report type of the compression.
- Execute [Citellus](https://github.com/citellusorg/citellus/)(SBR OpenStack Support Team Validation tool) on to the SOS Report.
- Gather solutions for the failed plugins.
- Publish the best of the solutions as a private comments on the case.


:pencil: **Feature**: Integrated Prometheus client in the application. If any error occurs, Prometheus metrics are pushed to pushgateway.

- To Setup Pushgateway in OpenShift Namespace:

	```shell
	$ oc tag prom/pushgateway:latest prom/pushgateway:latest
	$ oc new-app --docker-image=prom/pushgateway --name=pushgateway
	$ oc expose svc/pushgateway
	```
	- Pull the Prometheus image to OpenShift Namespace
	- Creates a Deploymentconfig and service
	- Expose the service to a route

### Running the Application

The Application can be cloned or downloaded from Github or else use the following code:
```
$ git clone https://github.com/harshad16/sbr-openstack
```

* On OpenShift:
	- After [deployment](https://github.com/harshad16/sbr-openstack#deployment) of the application.
	> The application would be created as a build images and a flask application would be running.</br>
	> Once a user submits a ticket with auth credentials on the POC website.</br>
	> Then a OpenShift Job would be deployed to process the ticket along with storing all the credential in OpenShift Secrets for Security.</br>
	> After the successful execution of the job, a private comment would be published on customer case.</br>
	> If execution fails the error would be reported to the developer and to the user on the POC Website.</br>

* To run the application in local system, Use Docker.

	- create a passwordfile with RHN password 
	- Edit the [Dockerfile](https://github.com/harshad16/sbr-openstack/blob/0c03a55c039cf404fa026622d5a2f09ab8f17d29/Dockerfile#L16) and add `COPY ./passwordfile /secret/` 
	- Use Following commands to execute:
	```shell
	$ docker build -t sbr .
	$ docker run --network host -it -e USERNAME=<RHN Username> -e TICKET=<customer ticket> -e SERVER=<collabrador or fubar> sbr bash 
	```

## Deployment

The Application is to be deployed on OpenShift cluster.

- Using Ansible Playbook:

	- Provision the deployment:
	```ansible
	ansible-playbook --extra-var="OCP_URL=<openshit_url>  OCP_TOKEN=<openshift_service_account_token> SBR_INFRA_NAMESPACE= <openshift_namespace> SBR_APPLICATION_NAMESPACE=<openshift_namespace>" playbooks/provision.yaml
	```

	- Deprovision the deployment:
	```ansible
	ansible-playbook --extra-var="OCP_URL=<openshit_ur>  OCP_TOKEN=<openshift_service_account_token> SBR_INFRA_NAMESPACE=<openshift_namespace> SBR_APPLICATION_NAMESPACE=<openshift_namespace>" playbooks/deprovision.yaml
	```

- The Project could be deployed using `oc commands` directly, please check the [provision.yaml](https://github.com/harshad16/sbr-openstack/tree/master/playbooks) file.

## Built With

* Python
* Docker 
* OpenShift API's
* OpenShift Container's
* Ansible

## Authors

* **Harshad Reddy Nalla** - *Initial work* - [harshad16](https://github.com/harshad16)

See also the list of [contributors](https://github.com/harshad16/sbr-openstack/graphs/contributors) who participated in this project.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE.md](https://github.com/harshad16/sbr-openstack/blob/master/LICENSE) file for details

## Disclaimer

This project is designed for **Red Hat** internal usage only.

## Acknowledgments

* [Citellus](https://github.com/citellusorg/citellus/)
* [Team Thoth](https://github.com/thoth-station)
* [SBR OpenStack Supporter Bot Trello Board](https://trello.com/b/wuNrAjoP/sbr-openstack)
