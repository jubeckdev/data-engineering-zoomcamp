# Azure foundation for the portfolio project

**Status: deployed and storage access verified on 23 November 2026.**
Terraform created the resource group, ADLS Gen2 account, three filesystems and
operator data permissions in Switzerland North. `verify_storage.py` successfully
uploaded, downloaded, compared and deleted a tiny synthetic test blob using
Entra ID authentication. See [verification.json](verification.json).

The deployment uses Azure free-trial credit. On 23 November 2026 the portal
showed €179.54 remaining, expiring 22 December 2026. Trial spending protection
remains enabled; the account has not been upgraded to paid billing.
The storage foundation has been extended by `platform.tf` for the capstone. See the platform section below and the [project README](../../README.md) for current scope.

Run `python3 verify_storage.py` from this directory to repeat the storage test.

## Resources and architecture

This configuration creates one dedicated resource group and a Standard LRS Hot
StorageV2 account in `switzerlandnorth`, with hierarchical namespaces enabled
(Azure Data Lake Storage Gen2). Three filesystems organize future data:

| Filesystem | Purpose |
| --- | --- |
| `bronze` | Original source data and ingestion metadata |
| `silver` | Cleaned, typed, deduplicated records |
| `gold` | Aggregated tables for dashboards |

It also grants the signed-in Terraform operator `Storage Blob Data Contributor`
on this storage account. The account uses Microsoft Entra authentication, TLS
1.2+, and HTTPS. Anonymous blob access and shared-key access are disabled.

The HTTPS endpoint remains reachable from the public internet so local clients
can authenticate to it. This is private **data**, not private-endpoint network
isolation. No virtual machines, Databricks clusters, or paid private endpoints are created. The optional platform adds a Basic Azure SQL database. Storage capacity, operations, and data transfer
can still cost money; this is not a guarantee of free usage. LRS is a small
development setup and does not protect against a whole-region outage.

## Validate locally without an Azure account

From this directory, with Docker Desktop running:

```bash
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.13.5 init -backend=false -input=false
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.13.5 fmt -check
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.13.5 validate
```

These commands initialize providers and check syntax/schema; they do not verify
Azure permissions, available regional capacity, account-name availability, or
actual deployment. Provider versions and checksums are pinned in the configuration
and `.terraform.lock.hcl`.

## Authenticate and configure a future deployment

Use the host Azure CLI and Terraform for deployment: the Terraform-only Docker
image above does not contain `az` for Azure CLI authentication. Install the
[Azure CLI for macOS](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos)
and [Terraform](https://developer.hashicorp.com/terraform/install) when ready.

In Azure, the operator needs permission to create resource groups and storage
accounts, plus permission to assign the account-scoped data role. Subscription
Owner has both; Contributor alone cannot create role assignments. Existing
organization accounts may require an administrator to grant the needed rights.

```bash
az login
az account list --output table
az account set --subscription YOUR_SUBSCRIPTION_ID
az account show --query '{name:name,id:id,state:state}' --output table

cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with that subscription UUID and a globally unique storage
account name (3–24 lowercase letters or digits). Keep `switzerlandnorth` unless
your subscription restricts it. Use a dedicated resource group and keep this
directory's state for all future changes.

After choosing the subscription and confirming the project budget, register the
Storage resource provider if it is not already registered:

```bash
az provider show --namespace Microsoft.Storage --query registrationState --output tsv
# Only if the preceding result is not Registered:
az provider register --namespace Microsoft.Storage --wait
```

The Terraform provider is configured to avoid automatically registering unrelated
resource providers. Sign in interactively; do not put passwords, access keys, or
Azure CLI token caches in this repository.

## Plan, review, deploy, and inspect

Only proceed after checking subscription credit and agreeing on the spending
limit. Azure budget alerts notify you; they are not a hard spending cap.

```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=deployment.tfplan
terraform show deployment.tfplan
# Execute the reviewed plan when ready to create the resources:
terraform apply deployment.tfplan
terraform output
```

The first apply waits 60 seconds after granting data permissions. Azure role
propagation sometimes takes longer: if filesystem creation returns a 403, verify
the role assignment, wait a few minutes, then generate and review a fresh plan.
Do not create a second storage account to work around permission propagation.

Check the actual filesystem names after deployment:

```bash
az storage fs list \
  --account-name "$(terraform output -raw storage_account_name)" \
  --auth-mode login --query '[].name' --output table
```

Local Terraform state may contain sensitive provider attributes even though no
secrets are explicitly output. State, variable values, and saved plan files are
ignored by Git. Keep local state secure and backed up; move to an appropriately
secured remote backend before sharing deployment ownership or adding CI/CD.

## Cleanup

The cleanup below deletes the managed filesystems and their data, storage
account, role assignment, and resource group. Export any data you want to keep
first and inspect the plan before executing it. Keep all unrelated resources
outside this dedicated group.

```bash
terraform plan -destroy -out=destroy.tfplan
terraform show destroy.tfplan
terraform apply destroy.tfplan
```

## References

- [Storage account Terraform resource, pinned provider version](https://registry.terraform.io/providers/hashicorp/azurerm/4.66.0/docs/resources/storage_account)
- [ADLS Gen2 filesystem Terraform resource](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_data_lake_gen2_filesystem)
- [Azure storage account types and naming](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview)
- [Azure role assignment permissions](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-portal)
- [Azure budgets and alerts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)

## Cost check on 23 November 2026

The subscription API confirmed trial spending protection is `On`. The first
resource-group query was rate limited. A later query succeeded and reported
**€0.0000436267 month-to-date before tax**. See [cost observation](cost-observation.json).
Cost reports can lag; this is not a final bill or a live credit balance.
This historical observation predates the SQL/Container Apps platform. Local Docker workloads do not consume Azure compute credit. The subscription remains on the free trial with spending protection enabled.
Budget alerts remain to be configured.

## Capstone platform (24 November 2026)

Set `enable_platform = true` to create a Basic Azure SQL database (5 DTU, 2 GB), a private Basic container registry, a user-assigned managed identity, a Consumption Container Apps environment and a Log Analytics workspace. The SQL server uses Entra-only authentication. It is in France Central because this subscription rejected Switzerland North and West Europe SQL provisioning; the remaining resources stay in Switzerland North.

Register the relevant providers first: `Microsoft.Sql`, `Microsoft.App`, `Microsoft.ContainerRegistry`, `Microsoft.OperationalInsights` and `Microsoft.ManagedIdentity`. Wait for each registration to finish. Provider availability and SKU lists do not guarantee resource creation; the actual successful deployment is the evidence.

The SQL firewall has an optional single-IP operator rule for initial setup and an Azure-services rule for the job. The latter permits network access from Azure services beyond this subscription; Entra database authorization is still required. This development topology is not private network isolation. Remove the temporary operator rule after validation.

Set `pipeline_image` to the private registry's immutable image digest to add the scheduled job. The managed identity can pull from this registry and read/write this dedicated lake. The owner initializes a contained SQL user with the managed identity client ID as its SID and rights scoped to the `analytics` schema; Azure RBAC uses the distinct principal/object ID. The job has no server-admin role or stored password.

```bash
# From capstone/, build for Azure's amd64 runtime:
docker buildx build --platform linux/amd64 --load -t swiss-rail-pipeline:VERSION .
az acr login --name REGISTRY_NAME
docker tag swiss-rail-pipeline:VERSION REGISTRY_NAME.azurecr.io/swiss-rail-pipeline:VERSION
docker push REGISTRY_NAME.azurecr.io/swiss-rail-pipeline:VERSION
# Put the returned registry@sha256 digest in the ignored platform variables,
# then review/apply a new Terraform plan from infra/azure/.
az containerapp job start --name job-swiss-rail --resource-group rg-zoomcamp-portfolio-dev
az containerapp job execution list --name job-swiss-rail --resource-group rg-zoomcamp-portfolio-dev --output table
```

SQL and registry storage continue to consume trial credit between runs. The job allows one 1-vCPU/2-GiB replica, a 900-second timeout and one retry. Its first-of-month 06:00 UTC schedule checks a slowly changing annual dataset. The log workspace has 30-day retention and a 0.1 GB/day ingestion quota; this is not an overall subscription cost cap.

## Final verification (25 November 2026)

The managed-identity job `job-swiss-rail-3evilpd` succeeded. Its lake verification object and dashboard were downloaded and reconciled with Azure SQL; see [cloud evidence](../../evidence/cloud-verification.json). The earlier failed identity mapping is documented in the project history. SQL rollback and replay tests passed. The temporary operator SQL firewall rule was removed afterward.

The latest Cost Management query reported approximately **EUR 0.16186** month-to-date before tax for this resource group. Spending protection was **On**. Reporting lags and may omit recent usage; this is not the remaining trial balance or a final bill. The old November 23 value above is historical.
