# AWS integration

The AWS mode uses boto3 and Amazon CloudWatch. Configure AWS credentials using the normal AWS SDK credential chain, set `AWS_MODE=true`, set `AWS_REGION`, and provide `EC2_INSTANCE_IDS` / `RDS_INSTANCE_IDS`.

The application does not store AWS secrets. For environments without AWS credentials, use local simulation mode.
