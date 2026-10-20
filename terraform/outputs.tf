output "load_balancer_dns_name" {
  description = "Point the API's domain (CNAME or alias) here."
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "Push images here."
  value       = aws_ecr_repository.api.repository_url
}

output "deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN variable in GitHub to enable deploys."
  value       = aws_iam_role.deploy.arn
}

output "alarm_topic_arn" {
  description = "Subscribe other targets (chat, paging) to alarms here."
  value       = aws_sns_topic.alarms.arn
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.api.name
}

output "private_subnet_ids" {
  description = "For one-off tasks such as seeding."
  value       = aws_subnet.private[*].id
}

output "api_security_group_id" {
  description = "For one-off tasks such as seeding."
  value       = aws_security_group.api.id
}
