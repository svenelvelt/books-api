# Production infrastructure on AWS

This Terraform describes how the Books API runs in production. CI checks it with `terraform fmt` and `terraform validate` on every push (Terraform 1.16, AWS provider 6.x, MongoDB Atlas provider 2.x). It has not been applied to real accounts.

## The two questions

### Where does the container run?

On ECS Fargate, in private subnets across two availability zones, behind an Application Load Balancer. Images are stored in ECR. There are no servers to manage, and two or more tasks keep the API up if a zone fails.

### Where is the database, and how does the container reach it?

In MongoDB Atlas: a three-node replica set in the same region, reached over AWS PrivateLink, so traffic stays inside AWS and the cluster has no public access. The tasks sign in with their IAM role, so no database password exists anywhere.

| Component | Resources | File |
|---|---|---|
| Network | VPC, 2 public and 2 private subnets, internet gateway, NAT gateway | `network.tf` |
| Entry point | ALB with HTTPS (HTTP redirects), target group | `alb.tf` |
| Compute | ECS cluster, task definition, service, autoscaling, logs | `ecs.tf` |
| Images | ECR repository with immutable tags and scan on push | `ecr.tf` |
| Database | Atlas project, cluster, PrivateLink endpoint, IAM database user | `database.tf` |
| Access | ECS roles, GitHub OIDC provider and deploy role | `iam.tf` |
| Firewall | One security group per hop: ALB → tasks → Atlas endpoint | `security.tf` |
| Monitoring | CloudWatch alarms and an SNS topic for notifications | `monitoring.tf` |

## Decisions

### Compute: ECS Fargate

EKS would be a cluster to run for a single service, and EC2 means patching hosts. Fargate runs the existing image as it is. A failed release rolls back automatically through the deployment circuit breaker.

### Database: Atlas

Atlas runs the same MongoDB major version that the tests run against. DocumentDB is only MongoDB-compatible: before relying on it, the aggregations here, such as the `$lookup` with a sub-pipeline behind `GET /authors`, would have to be verified against it. Self-managed MongoDB on EC2 would make replica sets, backups and upgrades our job. The trade-off is a second Terraform provider and an Atlas account. The cluster is pinned to 8.0, the long-term support release, so upgrades happen on purpose. CI and Docker Compose use 8.2 for now, because the 8.0 image refuses to start on recent Linux kernels ([SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912)); they can move back to 8.0 once a fixed 8.0 release is out.

### Hardening

The tasks run as a non-root user with a read-only root filesystem. The task roles can be assumed only by ECS on behalf of this account, which prevents another account's service from using them. The load balancer drops invalid headers and has deletion protection, and the API only trusts `X-Forwarded-For` from inside the VPC, so clients cannot fake their IP.

### Database access: IAM instead of a password

Atlas maps the ECS task role to a database user that can only `readWrite` the `books` database on this cluster. PyMongo signs in with the task's temporary AWS credentials (`authMechanism=MONGODB-AWS`, through the `pymongo[aws]` dependency). As a result the connection string holds no secret and is a plain environment variable, there is nothing to rotate, and access is revoked by changing IAM.

### Outbound traffic: one NAT gateway

The tasks need outbound access for ECR and CloudWatch Logs. A single NAT gateway is the simplest option. If its zone fails, outbound traffic stops: new tasks cannot pull images, and logs are buffered, because the log driver is non-blocking. Running tasks keep serving, and the database path, PrivateLink, is unaffected. The alternatives are one NAT gateway per zone, which costs double, or VPC endpoints with no internet route at all, which is stricter but means one endpoint per AWS service.

### Two health checks

The ALB target group checks `/health/ready`: a task that cannot reach MongoDB stops receiving traffic. The container health check uses `/health/live`: only a stuck process is replaced. A database outage therefore takes tasks out of rotation without ECS replacing every one of them.

### Scaling on requests, not CPU

The API mostly waits on MongoDB, so CPU stays low under load. Target tracking on `ALBRequestCountPerTarget` scales between 2 and 6 tasks.

### Terraform owns the infrastructure, CI owns releases

On every push to `main` that passes CI, GitHub Actions assumes the deploy role through OIDC, with no AWS keys stored in GitHub. It pushes an image tagged with the commit SHA and rolls out a new task definition revision. The deploy role can push only to this ECR repository and update only this service, but it can register task definitions that use the task role. Code merged to `main` therefore runs with database access, which is inherent to deploying from CI; branch protection on `main` is the control. The service ignores task definition and task count changes, so a later `terraform apply` does not undo a release or a scale-out. The flip side is that container settings changed in Terraform, such as environment variables or CPU, take effect with the next deploy from CI.

### Monitoring

CloudWatch alarms cover what users would notice first: a 5xx rate above 5% of requests, any task failing readiness for three minutes, a p95 response time above one second, and task CPU or memory above 80%. The error alarm uses a rate rather than a count, so the same threshold works at any traffic level. Alarms and recoveries go to an SNS topic, with an optional email subscription through `alarm_email`; chat or paging tools can subscribe to the same topic.

The API logs one JSON line per request to CloudWatch Logs, with a request ID that is also returned to the client. When an alarm fires, CloudWatch Logs Insights finds the requests behind it:

```
fields @timestamp, method, path, status, duration_ms, request_id
| filter logger = "app.access" and status >= 500
| sort @timestamp desc
| limit 50
```

### State

State is kept in S3 with native lock files. The bucket and key are supplied at `init`, so separate environments can use the same code with different state. The bucket should be versioned and encrypted. Because the database uses IAM authentication, the state holds no database credentials.

## Deploying

Requirements: Terraform 1.11 or newer, AWS credentials, an Atlas organization with a service account (set `MONGODB_ATLAS_CLIENT_ID` and `MONGODB_ATLAS_CLIENT_SECRET`), an ACM certificate for the API's domain, and an S3 bucket for state. An AWS account can have only one GitHub OIDC provider; if it already exists, import it with `terraform import aws_iam_openid_connect_provider.github <arn>` instead of creating it.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in the values
terraform init -backend-config="bucket=<state-bucket>" \
  -backend-config="key=books-api/prod.tfstate" -backend-config="region=eu-west-1"

# 1. Create the image repository and push a first image.
terraform apply -target=aws_ecr_repository.api
REPO=$(terraform output -raw ecr_repository_url)
TAG=$(git rev-parse --short HEAD)
aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build --platform linux/amd64 -t "$REPO:$TAG" .. && docker push "$REPO:$TAG"

# 2. Replace the placeholder tag, then create everything else (the Atlas
#    cluster and PrivateLink take a while).
sed -i.bak "s/^image_tag = .*/image_tag = \"$TAG\"/" terraform.tfvars
terraform apply
```

If the first `apply` fails because the cluster has no private connection string yet, Atlas has not published it; running `terraform apply` again picks it up.

Then:

1. Point the domain at `terraform output load_balancer_dns_name`.
2. In the GitHub repository, set the variables `AWS_DEPLOY_ROLE_ARN` (from `terraform output deploy_role_arn`) and `AWS_REGION`. From then on, every push to `main` deploys.
3. Optionally, load the sample data with a one-off task:
   ```bash
   SUBNET=$(terraform output -json private_subnet_ids | jq -r '.[0]')
   SG=$(terraform output -raw api_security_group_id)
   aws ecs run-task --cluster books-api --task-definition books-api --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG]}" \
     --overrides '{"containerOverrides":[{"name":"api","command":["python","-m","app.seed"]}]}'
   ```

## Not included

- Atlas alerts sent to the same SNS topic, and a CloudWatch dashboard
- AWS WAF on the load balancer, and the domain and certificate in Route 53 and ACM
- ALB access logs and VPC flow logs
- A staging environment: the same code with a second state key and `tfvars` file
- An approval gate for production deploys: a GitHub Environment with required reviewers, with the deploy role's trust narrowed to that environment
- Blue/green deployments (native in ECS) that roll back on the 5xx alarm, so a release that passes health checks but fails real requests is rolled back by switching traffic, not by redeploying
