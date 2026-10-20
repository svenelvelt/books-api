# Alarms notify an SNS topic. Not encrypted with the AWS-managed SNS key on
# purpose: CloudWatch can't publish to topics that use it.
resource "aws_sns_topic" "alarms" {
  name = "${var.name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alarm_email == null ? 0 : 1

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

locals {
  alarm_actions = [aws_sns_topic.alarms.arn]

  target_group_dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
}

# A rate rather than a count, so the threshold means the same at any traffic.
resource "aws_cloudwatch_metric_alarm" "error_rate" {
  alarm_name          = "${var.name}-5xx-rate"
  alarm_description   = "More than 5% of requests get a 5xx from the API."
  comparison_operator = "GreaterThanThreshold"
  threshold           = 5
  evaluation_periods  = 3
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  metric_query {
    id          = "rate"
    expression  = "100 * errors / requests"
    label       = "5xx rate (%)"
    return_data = true
  }

  metric_query {
    id = "errors"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      stat        = "Sum"
      period      = 60
      dimensions  = local.target_group_dimensions
    }
  }

  metric_query {
    id = "requests"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      stat        = "Sum"
      period      = 60
      dimensions  = local.target_group_dimensions
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "unhealthy_tasks" {
  alarm_name          = "${var.name}-unhealthy-tasks"
  alarm_description   = "A task fails readiness, for example because it can't reach MongoDB."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  dimensions          = local.target_group_dimensions
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "slow_responses" {
  alarm_name          = "${var.name}-slow-responses"
  alarm_description   = "The slowest 5% of requests take more than a second."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  dimensions          = local.target_group_dimensions
  extended_statistic  = "p95"
  period              = 60
  evaluation_periods  = 5
  comparison_operator = "GreaterThanThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "ecs" {
  for_each = {
    cpu    = "CPUUtilization"
    memory = "MemoryUtilization"
  }

  alarm_name          = "${var.name}-${each.key}-high"
  alarm_description   = "Average ${each.key} use of the API's tasks is above 80%."
  namespace           = "AWS/ECS"
  metric_name         = each.value
  dimensions          = { ClusterName = aws_ecs_cluster.main.name, ServiceName = aws_ecs_service.api.name }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}
