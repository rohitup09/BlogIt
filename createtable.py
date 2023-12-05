# -*- coding: utf-8 -*-
"""
Created on Fri Jul 10 20:36:03 2020

@author: hp
"""

import boto3
# Get the service resource.
import key_config as keys

dynamodb = boto3.resource('dynamodb',
                    aws_access_key_id=keys.ACCESS_KEY_ID,
                    aws_secret_access_key=keys.ACCESS_SECRET_KEY,
                    aws_session_token=keys.AWS_SESSION_TOKEN)



table_name = 'BlogPosts'
key_schema = [{'AttributeName': 'PostID', 'KeyType': 'HASH'}]
attribute_definitions = [{'AttributeName': 'PostID', 'AttributeType': 'S'}]

# Create the table
try:
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=key_schema,
        AttributeDefinitions=attribute_definitions,
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    print(f"Table {table_name} created successfully.")
except dynamodb.exceptions.ResourceInUseException:
    print(f"Table {table_name} already exists.")