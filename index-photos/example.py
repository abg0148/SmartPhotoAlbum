import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    print('Hello')
    
    # Initialize AWS clients
    ses = boto3.client("ses", region_name="us-east-1")
    sqs = boto3.resource("sqs", region_name="us-west-1")
    dynamodb = boto3.resource('dynamodb', region_name="us-west-1")
    table = dynamodb.Table('yelp-restaurants')
    
    #credentials = boto3.Session(aws_access_key_id=aws_access_key_id,
    #                            aws_secret_access_key=aws_secret_access_key).get_credentials()
    #aws_auth = AWS4Auth(credentials.access_key, credentials.secret_key, "us-west-1", "es")
    #es = elasticsearch.Elasticsearch(
    #    hosts=[{"host": 'search-mydomain-rmudkaleeyojuoyjjclqdwrbzm.aos.us-east-1.on.aws', "port": 443}],
    #    http_auth=aws_auth,
    #    use_ssl=True,
    #    verify_certs=True,
    #    connection_class=elasticsearch.RequestsHttpConnection
    #)
    
    # Define your OpenSearch parameters
    es_host = "search-mydomain-rmudkaleeyojuoyjjclqdwrbzm.aos.us-east-1.on.aws"
    region = "us-east-1"  # Replace with your AWS region

    auth = BotoAWSRequestsAuth(
        aws_host=es_host,
        aws_region=region,
        aws_service='es'
    )

    es = OpenSearch(
        hosts=[{"host": es_host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=27
    )
    
    queue = sqs.get_queue_by_name(QueueName="Q1")
    
    for msg in queue.receive_messages():
        req = json.loads(msg.body)
        # Query restaurant
        res = es.search(body={
            "query": {
                "function_score": {
                    "query": {
                        "match": {"Restaurant.cuisine": req["Cuisine"]},
                    },
                    "random_score": {}
                },
            },
            "size": 3
        }, index="restaurants", doc_type="_doc")
        print(res)

        ids = [res["hits"]["hits"][i]["_id"] for i in range(min(3, len(res["hits"]["hits"])))]
        print(ids)

        restaurants = [q["Items"][0] for q in [table.query(KeyConditionExpression=Key("id").eq(rid)) for rid in ids]]
        print(restaurants)

        # Send email
        response = ses.send_email(
            Source="alper.mumcular@ug.bilkent.edu.tr",  # Replace with your verified sender email address
            Destination={
                "ToAddresses": [req["EmailAddress"]]
            },
            Message={
                "Subject": {
                    "Data": f"Restaurant Suggestions for {req['Cuisine']}",
                    "Charset": "UTF-8"
                },
                "Body": {
                    "Text": {
                        "Data": (
                            f"Hello! Here are my {req['Cuisine']} restaurant "
                            f"suggestions for {req['NumberOfPeople']} people, for {req['DiningDate']} at {req['DiningTime']}: "
                            f"1. {restaurants[0]['name']}, located at {''.join(restaurants[0]['location']['display_address'])}, "
                            f"2. {restaurants[1]['name']}, located at {''.join(restaurants[1]['location']['display_address'])}, "
                            f"3. {restaurants[2]['name']}, located at {''.join(restaurants[2]['location']['display_address'])}. "
                            f"Enjoy your meal!"
                        ),
                        "Charset": "UTF-8"
                    }
                }
            }
        )
        print("Email sent! Message ID:", response['MessageId'])
        msg.delete()

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }