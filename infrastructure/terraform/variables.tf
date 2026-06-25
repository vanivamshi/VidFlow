variable "aws_region" {
  default = "us-east-1"
}

variable "project_name" {
  default = "ai-video"
}

variable "environment" {
  default = "dev"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "availability_zones" {
  default = ["us-east-1a", "us-east-1b"]
}

variable "private_subnet_cidrs" {
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  default = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "node_min_size" {
  default = 2
}

variable "node_max_size" {
  default = 10
}

variable "node_desired_size" {
  default = 3
}

variable "rds_instance_class" {
  default = "db.t3.medium"
}

variable "db_username" {
  default = "aivideo"
}

variable "db_password" {
  sensitive = true
}
