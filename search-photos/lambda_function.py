import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth

def lambda_handler(event, context):
    print("EVENT")
    print(event)
    
    client = boto3.client('lexv2-runtime', region_name='us-east-1')

    response = client.recognize_text(
        botId='OQHTJUKUR2',
        botAliasId='L3RYBMLZQT',
        localeId='en_US',
        sessionId='search-photos-role-nst1g6ho',
        text= event["queryStringParameters"]["q"]
    )

    slots = response.get('sessionState', {}).get('intent', {}).get('slots', {})

    labels = [slot['value']['interpretedValue'].lower() for slot in slots.values() if slot]

    host = 'search-photos-rstk2zrqrg6i3b2rgkhxmympzq.aos.us-east-1.on.aws'
    region = 'us-east-1'

    auth = BotoAWSRequestsAuth(
        aws_host=host,
        aws_region=region,
        aws_service='es'
    )

    opensearch = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    must_clauses = [{"match": {"labels": label}} for label in labels if label]
    query = {
        "query": {
            "bool": {
                "should": must_clauses,
                "minimum_should_match": 1
            }
        }
    }

    opensearch_response = opensearch.search(index='photos', body=query)

    images = []
    for image in opensearch_response['hits']['hits']:
        images.append('https://alper-hw3-b2.s3.us-east-1.amazonaws.com/'+ image['_source']['objectKey'])

    return  {
                'statusCode':200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-Api-Key, Authorization',
                },
                'body': json.dumps(images)
            }
