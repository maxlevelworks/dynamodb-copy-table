#!/usr/bin/env python
import boto3
import botocore
import sys
import os
from tqdm import tqdm

if len(sys.argv) != 3:
    print(f'Usage: {sys.argv[0]} <source_table_name> <destination_table_name>')
    sys.exit(1)

src_table = sys.argv[1]
dst_table = sys.argv[2]
region = os.getenv('AWS_DEFAULT_REGION', 'eu-west-1')

ddb = boto3.resource('dynamodb', region_name=region)
client = boto3.client('dynamodb', region_name=region)

# 1. Read and copy the source table to be copied
try:
    _ = client.describe_table(TableName=src_table)
    _ = client.describe_table(TableName=dst_table)
except botocore.exceptions.ResourceNotFoundException as e:
    print(f'Table {src_table} or {dst_table} does not exist: {e}') 
    sys.exit(1)
else:
    src = ddb.Table(src_table)
    dst = ddb.Table(dst_table)

print(f'*** Reading key schema from table {src_table}')
hash_key, range_key = None, None
for schema in src.key_schema:
    if schema['KeyType'] == 'HASH':
        hash_key = schema['AttributeName']
    elif schema['KeyType'] == 'RANGE':
        range_key = schema['AttributeName']

# 2. Copy the items and add the items
# Note: this is a very inefficient way of doing this 
# (store all old items in memory, insert them one by one)
print(f'Downloading items from source {src_table}')
src_response = src.scan()
old_items = src_response['Items']
while 'LastEvaluatedKey' in src_response:
    print(src_response['LastEvaluatedKey'])
    src_response = src.scan(ExclusiveStartKey=src_response['LastEvaluatedKey'])
    old_items.extend(src_response['Items'])

print(f'Downloaded {len(old_items)} old items to copy to {dst_table}')

for old_item in tqdm(old_items):
    new_item = {hash_key: old_item[hash_key]}
    if range_key is not None: new_item[range_key] = old_item[range_key]
    for k, v in old_item.items():
        if k not in (hash_key, range_key):
            new_item[k] = v
    _ = dst.put_item(Item=new_item)

print('Done.')
