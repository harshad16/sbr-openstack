# SBR OpenStack Supporter Bot Project
The SBR OpenStack Supppoter bot project is sponsered by Red Hat Inc.It is an application for Red Hat SBR OpenStack Support Team.The application serves as automation for the customer case ticket processing, it process the ticket by performing following actions:
- Fetching relevant information (attachments,SOS Reports).
- Extracting the SOS Report from the attachment based upon the SOS Report type of the compression.
- Execute Citellus(SBR OpenStack Support Team Validation tool) on to the SOS Report.
- Gather solutions for the failed plugins.
- Publish the best of the solutions as a private comments on the case.



#### Deploy the SBR OpenStack Supporter Bot Project on OpenShift:
- Using Ansible Playbook:
`ansible-playbook --extra-var="OCP_URL=< openshit_url >  OCP_TOKEN=< openshift_service_account_token > SBR_INFRA_NAMESPACE= < openshift_namespace > SBR_APPLICATION_NAMESPACE=< openshift_namespace >" playbooks/provision.yaml`

- Delete the deployment:
`ansible-playbook --extra-var="OCP_URL=< openshit_url >  OCP_TOKEN=< openshift_service_account_token > SBR_INFRA_NAMESPACE= < openshift_namespace > SBR_APPLICATION_NAMESPACE=< openshift_namespace >" playbooks/deprovision.yaml`

