# AWS Setup

1. Create or use an EC2 resource and an RDS instance in an AWS account you are authorized to use.
2. Ensure CloudWatch metrics are available for the resources.
3. Configure AWS credentials using an approved AWS credential mechanism (environment variables, AWS profile, instance role, etc.).
4. Copy `.env.example` to `.env`.
5. Set `AWS_MODE=true`, `AWS_REGION`, `EC2_INSTANCE_IDS` and `RDS_INSTANCE_IDS`.
6. Run `POST /api/aws/collect`.

The current adapter reads representative EC2 and RDS CloudWatch metrics. Exact metric availability depends on the AWS resource type and account configuration.
