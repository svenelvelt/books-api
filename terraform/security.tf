# Traffic is allowed only along one path:
# internet -> ALB (80/443) -> tasks (8000) -> Atlas endpoint (PrivateLink ports).

resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "Public HTTP(S) to the load balancer"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  description       = "Only redirected to HTTPS"
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_to_api" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_security_group" "api" {
  name        = "${var.name}-api"
  description = "ECS tasks running the API"
  vpc_id      = aws_vpc.main.id
}

resource "aws_vpc_security_group_ingress_rule" "api_from_alb" {
  security_group_id            = aws_security_group.api.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_egress_rule" "api_https" {
  description       = "AWS APIs through the NAT gateway: ECR, CloudWatch Logs"
  security_group_id = aws_security_group.api.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "api_to_atlas" {
  security_group_id            = aws_security_group.api.id
  referenced_security_group_id = aws_security_group.atlas_endpoint.id
  ip_protocol                  = "tcp"
  from_port                    = 1024
  to_port                      = 65535
}

resource "aws_security_group" "atlas_endpoint" {
  name        = "${var.name}-atlas-endpoint"
  description = "PrivateLink endpoint to MongoDB Atlas"
  vpc_id      = aws_vpc.main.id
}

# Atlas maps each cluster node to its own port on the endpoint, so PrivateLink
# needs a port range rather than 27017.
resource "aws_vpc_security_group_ingress_rule" "atlas_from_api" {
  security_group_id            = aws_security_group.atlas_endpoint.id
  referenced_security_group_id = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = 1024
  to_port                      = 65535
}
