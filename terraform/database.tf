locals {
  # Atlas names AWS regions in upper case with underscores: eu-west-1 -> EU_WEST_1.
  atlas_region = upper(replace(var.aws_region, "-", "_"))
}

# No IP access list: the cluster is only reachable through PrivateLink.
resource "mongodbatlas_project" "main" {
  name   = var.name
  org_id = var.atlas_org_id
}

resource "mongodbatlas_advanced_cluster" "main" {
  project_id   = mongodbatlas_project.main.id
  name         = var.name
  cluster_type = "REPLICASET"

  backup_enabled                 = true
  termination_protection_enabled = true

  replication_specs = [{
    region_configs = [{
      provider_name = "AWS"
      region_name   = local.atlas_region
      priority      = 7
      electable_specs = {
        instance_size = var.atlas_instance_size
        node_count    = 3
      }
    }]
  }]
}

# PrivateLink: an interface endpoint in the VPC to Atlas' endpoint service.
resource "mongodbatlas_privatelink_endpoint" "main" {
  project_id    = mongodbatlas_project.main.id
  provider_name = "AWS"
  region        = var.aws_region
}

resource "aws_vpc_endpoint" "atlas" {
  vpc_id             = aws_vpc.main.id
  service_name       = mongodbatlas_privatelink_endpoint.main.endpoint_service_name
  vpc_endpoint_type  = "Interface"
  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.atlas_endpoint.id]

  tags = { Name = "${var.name}-atlas" }
}

resource "mongodbatlas_privatelink_endpoint_service" "main" {
  project_id          = mongodbatlas_project.main.id
  private_link_id     = mongodbatlas_privatelink_endpoint.main.private_link_id
  endpoint_service_id = aws_vpc_endpoint.atlas.id
  provider_name       = "AWS"
}

# IAM auth: the ECS task role is the database user, so there's no password.
# The API signs in with the task's AWS credentials (MONGODB-AWS).
resource "mongodbatlas_database_user" "api" {
  project_id         = mongodbatlas_project.main.id
  auth_database_name = "$external"
  username           = aws_iam_role.task.arn
  aws_iam_type       = "ROLE"

  roles {
    role_name     = "readWrite"
    database_name = var.database_name
  }

  scopes {
    name = mongodbatlas_advanced_cluster.main.name
    type = "CLUSTER"
  }
}

# The private connection string only exists once the endpoint is accepted,
# so read the cluster again after that.
data "mongodbatlas_advanced_cluster" "main" {
  project_id = mongodbatlas_project.main.id
  name       = mongodbatlas_advanced_cluster.main.name

  depends_on = [mongodbatlas_privatelink_endpoint_service.main]
}

locals {
  private_srv = one([
    for endpoint in data.mongodbatlas_advanced_cluster.main.connection_strings.private_endpoint :
    endpoint.srv_connection_string
    if anytrue([for e in endpoint.endpoints : e.endpoint_id == aws_vpc_endpoint.atlas.id])
  ])

  mongodb_uri = "${local.private_srv}/?authSource=%24external&authMechanism=MONGODB-AWS&retryWrites=true&w=majority"
}
