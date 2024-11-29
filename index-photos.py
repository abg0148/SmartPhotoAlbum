import boto3
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth

def lambda_handler(event, context):
    # Auth & Get Services 
    host = 'search-photos-rstk2zrqrg6i3b2rgkhxmympzq.aos.us-east-1.on.aws'
    region = 'us-east-1'

    auth = BotoAWSRequestsAuth(
        aws_host=host,
        aws_region=region,
        aws_service='es'
    )

    s3 = boto3.client('s3')
    rekognition = boto3.client('rekognition')
    opensearch = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    # Get S3 Bucket
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Get Rekognition Labels
    response = rekognition.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':key}})
    rekognito_labels = [x['Name'].lower() for x in response['Labels']] if 'Labels' in response else []
    print(f'Rekognition Labels : {rekognito_labels}')

    # Get Custom Labels
    header = s3.head_object(Bucket=bucket, Key=key)
    custom_labels = header['ResponseMetadata']['HTTPHeaders'].get('x-amz-meta-customlabels', '').lower().split(',') if 'x-amz-meta-customlabels' in header['ResponseMetadata']['HTTPHeaders'] else []
    print(f'Custom Labels: {custom_labels}')

    labels = custom_labels + rekognito_labels
    
    response =  {
                    "objectKey": key,
                    "bucket": bucket,
                    'createdTimestamp': datetime.now().isoformat(),
                    "labels": labels,
                }

    print(f'response: {response}')

    # Add to OpenSearch
    opensearch.index(index = 'photos', id = key, body = response, refresh = True)
    print(f'Added to OpenSearch: id : {key}, body : {response}')

    return {
        'statusCode': 200,
        'body': 'Photo indexed.',
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,PUT',
        }
    }