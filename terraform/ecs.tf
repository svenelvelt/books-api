resource "aws_ecs_cluster" "main" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.name}"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "api" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    essential = true

    # Only trust X-Forwarded-For from the VPC (the ALB). With "*" clients could
    # fake their IP.
    command = [
      "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
      "--proxy-headers", "--forwarded-allow-ips", var.vpc_cidr,
    ]
    readonlyRootFilesystem = true
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }]

    environment = [
      { name = "MONGODB_URI", value = local.mongodb_uri },
      { name = "MONGODB_DATABASE", value = var.database_name },
    ]

    # Liveness only, so a MongoDB outage doesn't get every task replaced.
    healthCheck = {
      command = [
        "CMD", "python", "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')",
      ]
      interval    = 15
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
        # Don't block the app if CloudWatch is unreachable.
        mode            = "non-blocking"
        max-buffer-size = "25m"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = var.name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.min_tasks
  launch_type     = "FARGATE"

  health_check_grace_period_seconds = 30

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # CI deploys new revisions and autoscaling sets the count; don't revert them.
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.https]
}

resource "aws_appautoscaling_target" "api" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.min_tasks
  max_capacity       = var.max_tasks
}

# Scale on requests: the API mostly waits on MongoDB, so CPU stays low.
resource "aws_appautoscaling_policy" "requests" {
  name               = "${var.name}-requests"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value = var.requests_per_task

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
    }
  }
}
