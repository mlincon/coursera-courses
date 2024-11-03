import datetime as dt
import json
import logging
from random import randint

import boto3
import requests
from airflow import DAG
from airflow.operators.dummy import EmptyOperator
from airflow.operators.python import PythonOperator

# Assign the name of your _Raw Data Bucket_ to `DATA_BUCKET` constant 
# replacing the placeholder `<RAW-DATA-BUCKET>`
RAW_DATA_BUCKET = "de-c2w4lab1-730335434691-us-east-1-raw-data"

# Instantiate a boto3 client using method `boto3.client()`, establishing a 
# connection with `s3`
client = boto3.client("s3")

logger = logging.getLogger()
logger.setLevel("INFO")

# Define the directed acyclic graph:
with DAG(
    dag_id="book_of_the_day",
    
    # Set the `start_date` as a `datetime` object representing a
    # date 7 days before the current date. This can be done using the function 
    # `dt.timedelta()` with the parameter `days` equal to `7`
    start_date=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7),
    
    schedule="@daily",
    # Setting `catchup=True` (which is the default) in combination with a
    # `start_date` in the past means that, immediately after the DAG is
    # activated, Airflow will execute all the DAG runs corresponding to the
    # days between `start_date` and the current date. You'll take advantage of
    # that to have the DAG automatically run a few times as soon as you
    # activate it:
    catchup=True,
) as dag:

    start_task = EmptyOperator(task_id="start")

    def get_random_book(**context):
        
        # Get a random integer between 10,001 and 21,000,000 with function `randint`:
        random_book_id = randint(10_001, 21_000_000)

        # Use the previously obtained random number to get an Open Library work
        # ID:
        book_id = f"/OL{random_book_id}W"
        logger.info(f"SELECTED BOOK ID: {book_id}")

        # Make a call to the Open Library works API to retrieve information
        # about the book with the given ID:
        response = requests.get(
            f"https://openlibrary.org/works/{book_id}.json"
        )

        assert response.status_code == 200, response.reason

        # Some resources returned by the API are just pointers to another
        # resource and don't have the book title. In that case, we will raise
        # an assertion error so that Airflow retries the task:
        assert "title" in response.json()

        # Define the name of the object to be created with the initial
        # information about the book. `context['ds']` will correspond to the
        # logical date of the DAG run (the date when it was scheduled to run):
        file_name = f"initial_info_{context['ds']}.json"

        logger.info(f"Saving file: {file_name}")
        
        # Call the `put_object` method of the boto3 client by passing the
        # Raw Data Bucket constant to the Bucket parameter, and the content of the
        # API response to the Body parameter with the code `response.content`
        client.put_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"books/{context['ds']}/{file_name}",
            Body=response.content,
        )
        
        logger.info(f"File: {file_name} saved successfully")

    # Define the task that fetches the initial information about a random book
    # and stores it in S3:
    get_book_task = PythonOperator(
        task_id="get_random_book",
        python_callable=get_random_book, # Pass `get_random_book` function which you defined above
        retries=5,  # retry the task in case we get a resource with no title
        retry_delay=dt.timedelta(seconds=1),
    )

    def get_initial_info_dict(date: str):
        """
        Fetches the contents of the initial information file for the given date
        as a Python dictionary.
        """
        # Remember that the name of the file is of the form
        # "initial_info_<LOGICAL_DATE>.json":
        initial_info_file_name = f"initial_info_{date}.json"

        logger.info(f"Reading the file: {initial_info_file_name}")

        # Get the object corresponding to the file using method `get_object()`. 
        # Pass the Raw Data Bucket name to the Bucket parameter 
        # and the Key with the complete location of the 
        # "initial_info_<LOGICAL_DATE>.json" file in the bucket:
        initial_info_file = client.get_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"books/{date}/{initial_info_file_name}",
        )
        
        logger.info(f"File read: {initial_info_file_name}")

        assert (
            initial_info_file is not None
        ), f"The file {RAW_DATA_BUCKET}/books/{date}/{initial_info_file_name} does not exist"

        # Use the `"Body"` key in the response dictionary from the client
        # `get_object` method. Then, use the `read()` method to obtain
        # the context of the initial information file as a string:
        initial_info_string = initial_info_file["Body"].read()
        
        # Parse the contents of the initial information file, which is JSON, as
        # a Python dictionary:
        initial_info = json.loads(initial_info_string)

        return initial_info
    
    
    def get_author_names(**context):
        
        # Read the initial information about the book selected for the
        # corresponding day using the `get_initial_info_dict` function.
        # Remember that the DAG's logical date can be obtained from
        # `context["ds"]`:
        initial_info = get_initial_info_dict(context['ds'])
        
        # Initialize the list that will contain the authors' names:
        author_names = []

        # Fill the list of authors' names with the information retrieved from
        # Open Library's authors API. If there is no information about authors,
        # an empty list will be saved:
        for author in initial_info.get("authors", []):
            author_key = author["author"]["key"]  # API call suffix
            response = requests.get(
                f"https://openlibrary.org{author_key}.json"
            )
            author_names.append(response.json()["name"])

        # Serialize the list of authors' names as a string representing a JSON
        # array:
        author_names_string = json.dumps(author_names)

        # Construct the author's file name
        author_file_name = f"author_names_{context['ds']}.json"

        logger.info(f"Saving file: {author_file_name}")

        # Call the `put_object` method of the boto3 client by passing the
        # Raw Data Bucket name to the Bucket parameter, and 
        # the author_names_string to the Body parameter
        client.put_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"authors/{context['ds']}/{author_file_name}",
            Body=author_names_string,
        )

        logger.info(f"File: {author_file_name} saved")

    
    get_authors_task = PythonOperator(
        task_id="get_authors",
        # Pass the `get_author_names` to the `python_callabes` parameter
        python_callable=get_author_names,
    )


    def get_cover(**context):

        # Read the initial information about the book selected for the
        # corresponding day using the `get_initial_info_dict` function.
        # Remember that the DAG's logical date can be obtained from
        # `context["ds"]`:
        initial_info = get_initial_info_dict(context["ds"])

        if "covers" in initial_info:
            # Get the first cover ID from the list (there might be more than one):
            cover_id = initial_info["covers"][0]

            response = requests.get(
                f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            )

            # Construct the cover image file name
            cover_file_name = f"cover_{context['ds']}.jpg"

            logger.info(f"Saving File: {cover_file_name}")
            
            # Call the `put_object` method of the boto3 client by passing the
            # Raw Data Bucket name to the Bucket parameter, and the content of the
            # API response to the Body parameter
            client.put_object(
                Bucket=RAW_DATA_BUCKET,
                Key=f"covers/{context['ds']}/{cover_file_name}",
                Body=response.content,
            )
            
            logger.info(f"File: {cover_file_name} saved")

    get_cover_task = PythonOperator(
        task_id="get_cover",
        # Pass the `get_cover` to the `python_callable` parameter
        python_callable=get_cover,
        
    )

    
    def save_final_book_record(**context):
        
        # Read the initial information about the book selected for the
        # corresponding day using the `get_initial_info_dict` function.
        # Remember that the DAG's logical date can be obtained from
        # `context["ds"]`:
        initial_info = get_initial_info_dict(context["ds"])

        # Read the information about the authors as list of strings:
        authors_file_name = f"author_names_{context['ds']}.json"
        authors_object = client.get_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"authors/{context['ds']}/{authors_file_name}",
        )
        assert authors_object is not None

        authors = json.loads(authors_object["Body"].read())

        # Create book record
        book_record_dict = {
            "title": initial_info["title"],
            "authors": authors,
        }

        # If there is a cover in the initial info
        if "covers" in initial_info:
            cover_filename = f"cover_{context['ds']}.jpg"

            book_record_dict[
                "cover_uri"
            ] = f"s3://{RAW_DATA_BUCKET}/covers/{context['ds']}/{cover_filename}"

        # Serialize the `book_record_dict` as a JSON string:
        book_record_json = json.dumps(book_record_dict)

        # Prepare the book record file name 
        book_record_file_name = f"book_record_{context['ds']}.json"
        
        # Call the `put_object` method of the boto3 client by passing the
        # Raw Data Bucket name to the Bucket parameter, and the 
        # `book_record_json` to the Body parameter
        client.put_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"book_records/{context['ds']}/{book_record_file_name}",
            Body=book_record_json,
        )

    save_final_book_record_task = PythonOperator(
        task_id="save_final_book_record",
        # Pass the `save_final_book_record` to the `python_callable` parameter
        python_callable=save_final_book_record,
    )


    def clean_up_intermediate_info(**context):
        # Delete the initial information file of the logical date by using the
        # `delete_object` method of the boto3 client by passing the bucket
        # name and Key with the path to the object:
        initial_info_file_name = f"initial_info_{context['ds']}.json"

        client.delete_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"books/{context['ds']}/{initial_info_file_name}",
        )

        
        authors_file_name = f"author_names_{context['ds']}.json"
        
        # Delete the authors' names file of the logical date by using the
        # `delete_object` method of the boto3 client by passing the bucket
        # name and Key with the path to the object:
        client.delete_object(
            Bucket=RAW_DATA_BUCKET,
            Key=f"authors/{context['ds']}/{authors_file_name}",
        )

        # Note that the cover images should not be deleted.

    cleanup_task = PythonOperator(
        task_id="cleanup",
        # Pass the `clean_up_intermediate_info` to the `python_callable` parameter
        python_callable=clean_up_intermediate_info,
    )


    # Define the `end` task as a dummy operator with the `task_id` 
    # equal to `"end"`:
    end_task = EmptyOperator(task_id="None")
    
    # Define the task dependencies with the `>>` operator to obtain the desired
    # DAG:
    start_task >> get_book_task
    get_book_task >> [get_authors_task, get_cover_task]
    [get_authors_task, get_cover_task] >> save_final_book_record_task
    save_final_book_record_task >> cleanup_task
    cleanup_task >> end_task