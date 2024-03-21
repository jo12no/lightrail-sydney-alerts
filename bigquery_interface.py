"""Constructs the BigQuery client and performs operations for the primary script.
"""
import logging

import config
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError, NotFound

PROJECT_ID = config.PROJECT_ID
DATASET_ID = config.DATASET_ID
TABLE_ID = config.TABLE_ID
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# Set the logging level to INFO so that INFO messages get logged.
# pylint: disable=W1203
logging.basicConfig(level=logging.INFO)


def create_bq_client():
    """Creates a BigQuery client for the specified project.

    Returns:
        google.cloud.bigquery.client.Client: A BigQuery client instance.
    """
    return bigquery.Client(project=PROJECT_ID)


def check_table_exists(client):
    """Checks if the specified table exists in BigQuery.

    Args:
        client (google.cloud.bigquery.client.Client): A BigQuery client.

    Returns:
        bool: True if the table exists, False otherwise.

    Raises:
        GoogleCloudError: If an error occurs during the API request.
    """
    try:
        # Make an API request to check if the table exists.
        client.get_table(FULL_TABLE_ID)  # Make an API request.
        logging.info(f"Table {FULL_TABLE_ID} exists.\n")
        return True
    except NotFound as e:
        # If the table does not exist, NotFound exception is raised.
        logging.error(f"Table {FULL_TABLE_ID} does not exist: {e}")
        return False
    except GoogleCloudError as e:
        logging.error(f"Error checking if table exists: {e}")
        raise e


def create_new_table(client):
    """Creates a new table in BigQuery with the defined schema.

    Args:
        client (google.cloud.bigquery.client.Client): A BigQuery client.

    Raises:
        GoogleCloudError: If an error occurs while creating the table.
    """
    schema = [
        bigquery.SchemaField("alert_id", "STRING"),
        bigquery.SchemaField("url", "STRING"),
        bigquery.SchemaField("title", "STRING"),
        bigquery.SchemaField("description_html", "STRING"),
        bigquery.SchemaField("start_date", "STRING"),
        bigquery.SchemaField("end_date", "STRING"),
        bigquery.SchemaField("l1_line_impacted", "BOOLEAN"),
        bigquery.SchemaField("creation_date", "DATETIME"),  # CURRENT_DATETIME
    ]

    try:
        # Create a Table object
        table = bigquery.Table(FULL_TABLE_ID, schema=schema)
        table = client.create_table(table)
        logging.info(
            f"Table {TABLE_ID} created in dataset {DATASET_ID} in project {PROJECT_ID}."
        )
    except GoogleCloudError as e:
        logging.error(f"Error creating table: {e}")
        raise e


def check_alert_id_is_unique(client, processed_alert):
    """Checks if the alert ID is unique in the table.

    Args:
        client (google.cloud.bigquery.client.Client): A BigQuery client.
        processed_alert (dict): The processed alert data containing the alert ID.

    Returns:
        bool: True if the alert ID is unique, False otherwise.
    """
    alert_id = processed_alert["alert_id"]
    check_query = f"""
        SELECT COUNT(*)
        FROM `{DATASET_ID}.{TABLE_ID}`
        WHERE alert_id = @alert_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("alert_id", "STRING", alert_id),
            bigquery.ScalarQueryParameter("dataset", "STRING", DATASET_ID),
            bigquery.ScalarQueryParameter("table", "STRING", TABLE_ID),
        ]
    )
    query_job = client.query(check_query, job_config=job_config)
    results = query_job.result()

    # Check if the ID was found
    id_exists = False
    if next(results)[0] > 0:
        id_exists = True
        logging.info(f"id: {alert_id} already exists in table, skipping.")

    return id_exists


def insert_values_into_table(client, processed_alert):
    """Inserts values into the table based on the processed alert data.

    Args:
        client (google.cloud.bigquery.client.Client): A BigQuery client.
        processed_alert (dict): The processed alert data to be inserted.

    Raises:
        GoogleCloudError: If an error occurs while inserting rows into the table.
    """
    query = f"""
        INSERT INTO `{DATASET_ID}.{TABLE_ID}` (alert_id, url, title, description_html, start_date, end_date, l1_line_impacted, creation_date)
        VALUES (@alert_id, @url, @title, @description_html, @start_date, @end_date, @l1_line_impacted, CURRENT_DATETIME('Australia/Sydney'))
    """
    logging.info("Attempting to add new row into the BQ table.")
    logging.info(query)
    # Using named parameters for clarity and security
    query_params = [
        bigquery.ScalarQueryParameter(
            "alert_id", "STRING", processed_alert["alert_id"]
        ),
        bigquery.ScalarQueryParameter("url", "STRING", processed_alert["url"]),
        bigquery.ScalarQueryParameter("title", "STRING", processed_alert["title"]),
        bigquery.ScalarQueryParameter(
            "description_html", "STRING", processed_alert["description_html"]
        ),
        bigquery.ScalarQueryParameter(
            "start_date", "STRING", processed_alert["formatted_start_date"]
        ),
        bigquery.ScalarQueryParameter(
            "end_date", "STRING", processed_alert["formatted_end_date"]
        ),
        bigquery.ScalarQueryParameter(
            "l1_line_impacted", "BOOL", processed_alert["l1_line_impacted"]
        ),
    ]

    job_config = bigquery.QueryJobConfig(query_parameters=query_params)

    try:
        # Execute the query with parameters
        query_job = client.query(query, job_config=job_config)  # Make an API request.
        query_job.result()  # Wait for the query to finish
        logging.info("New row has been added!")
    except GoogleCloudError as e:
        # Handle exceptions raised by the client library
        logging.error(f"Encountered an error while inserting rows: {e}")
        raise e
