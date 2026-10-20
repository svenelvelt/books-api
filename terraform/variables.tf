variable "name" {
  description = "Name prefix for all resources."
  type        = string
  default     = "books-api"
}

variable "aws_region" {
  description = "AWS region for the API. The Atlas cluster runs in the same region."
  type        = string
  default     = "eu-west-1"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "certificate_arn" {
  description = "ACM certificate for the API's domain, used by the HTTPS listener."
  type        = string
}

variable "image_tag" {
  description = "Image tag for the task definition Terraform creates. Set it once to the first pushed image; later releases are deployed by CI."
  type        = string
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "min_tasks" {
  description = "Minimum number of running tasks. Two or more keeps the API up if one AZ fails."
  type        = number
  default     = 2
}

variable "max_tasks" {
  description = "Maximum number of running tasks."
  type        = number
  default     = 6
}

variable "requests_per_task" {
  description = "Target requests per task per minute. Autoscaling adds tasks above it."
  type        = number
  default     = 1000
}

variable "atlas_org_id" {
  description = "MongoDB Atlas organization that owns the project."
  type        = string
}

variable "atlas_instance_size" {
  description = "Atlas cluster tier. M10 is the smallest tier with private endpoints."
  type        = string
  default     = "M10"
}

variable "database_name" {
  description = "MongoDB database the API uses."
  type        = string
  default     = "books"
}

variable "alarm_email" {
  description = "Email address for alarm notifications. Without it, the alarm topic has no subscriber."
  type        = string
  default     = null
}

variable "github_repository" {
  description = "GitHub repository (owner/name) whose main branch may deploy."
  type        = string
  default     = "svenelvelt/books-api"
}
