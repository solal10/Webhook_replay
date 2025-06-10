#!/bin/bash

# Check bucket encryption
echo "Checking bucket encryption..."
aws --endpoint-url=http://localhost:4566 s3api get-bucket-encryption --bucket events-dev --output json

# Check public access block
echo -e "\nChecking public access block..."
aws --endpoint-url=http://localhost:4566 s3api get-public-access-block --bucket events-dev --output json
