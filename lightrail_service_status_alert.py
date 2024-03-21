"""Check if there are any alerts on the Sydney Lightrail lines by checking the TNSW API.

Adds new alerts to a BigQuery table and send the new entries to myself as an email. 

If the alert exists in the BigQuery table already, do not send an email since we don't
need to be notified. 

Intended to be hosted in Google Cloud Platform as a Cloud Function and scheduled to run
every 1 minute. 
"""
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bigquery_interface
import config
import requests

# Set the logging level to INFO so that INFO messages get logged.
# pylint: disable=W1203
logging.basicConfig(level=logging.INFO)

# API Constants
API_URL = "https://api.transport.nsw.gov.au/v2/gtfs/alerts/lightrail?format=json"
TNSW_API_KEY = config.TNSW_API_KEY if config.TNSW_API_KEY else os.getenv("TNSW_API_KEY")

# Email Configuration
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
EMAIL_FROM = config.EMAIL_FROM
EMAIL_TO = config.EMAIL_TO
EMAIL_FROM_KEY = config.EMAIL_FROM_KEY


def fetch_data():
    """Retrieves alert status data from the TNSW API for the Sydney Lightrail lines.

    This function sends a GET request to a specified API URL using an API key for 
    authorization. It expects the API to return a JSON response. If the request is 
    successful, it returns the parsed JSON data. In case of any network-related errors, 
    it logs the error and returns None.

    Args:
        None

    Returns:
        dict or None: The JSON response as a dictionary if the request is successful; 
        otherwise, None.

    Raises:
        requests.RequestException: If there's an error while making the GET request.

    """
    headers = {"Authorization": f"apikey {TNSW_API_KEY}"}

    try:
        response = requests.get(API_URL, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"An error occurred while fetching data: {e}")
        return None


def process_response_alert(entity):
    """Process an alert entity and extract relevant information.

    This function processes a dictionary representing an alert entity. It extracts the 
    alert's ID, URL, title, description, start and end dates, and whether a specific 
    line (IWLR-191) is impacted by the alert. The dates are formatted into a 
    human-readable string. If any required keys are missing or an error occurs 
    during processing, the function logs the error and returns None.

    Args:
        entity (dict): A dictionary containing alert details.

    Returns:
        dict or None: A dictionary with processed alert data if successful; 
        otherwise, None.

    Raises:
        KeyError: If a required key is missing in the input entity.
        Exception: If an unexpected error occurs during processing.

    """
    try:
        alert_id = entity["id"]
        url = entity["alert"]["url"]["translation"][0]["text"]
        title = entity["alert"]["headerText"]["translation"][0]["text"]
        description_html = entity["alert"]["descriptionText"]["translation"][0][
            "text"
        ].replace("\n", "")

        # date formatting
        try:
            start_timestamp = datetime.fromtimestamp(
                int(entity["alert"]["activePeriod"][0]["start"])
            )
            formatted_start_date = start_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted_start_date = "NULL"

        try:
            end_timestamp = datetime.fromtimestamp(
                int(entity["alert"]["activePeriod"][-1]["end"])
            )
            formatted_end_date = end_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted_end_date = "NULL"

        # impacted lines
        affected_lines_json = entity["alert"]["informedEntity"]
        l1_line_impacted = False
        for line in affected_lines_json:
            if line["routeId"] == "IWLR-191" and line["directionId"] == 1:
                l1_line_impacted = True
            elif line["routeId"] == "IWLR-191" and line["directionId"] == 0:
                l1_line_impacted = True

        processed_alert = {
            "alert_id": alert_id,
            "url": url,
            "title": title,
            "description_html": description_html,
            "formatted_start_date": formatted_start_date,
            "formatted_end_date": formatted_end_date,
            "l1_line_impacted": l1_line_impacted,
        }

        return processed_alert
    except KeyError as e:
        logging.error(f"Error processing alert: Missing key {e}")
        return None
    except Exception as e:
        logging.error(f"Error processing alert: {e}")
        return None


def format_email_body(processed_response_alert):
    """Constructs an email body string from a dictionary of processed response alerts.

    Args:
        processed_response_alert (dict): A dictionary where each key represents an 
        alert type, and the corresponding value is the alert's detailed information.

    Returns:
        str: A formatted email body string. Each line in the string contains an alert 
        type followed by its details, separated by a colon and a space.
    """
    email_body_str = ""
    for alert in processed_response_alert:
        email_body_str += f"{alert}: {processed_response_alert[alert]}\n"

    return email_body_str


def send_email(formatted_email_body):
    """Sends an email with a given body to a predefined recipient.

    This function constructs an email message using the `formatted_email_body` 
    parameter, sets the sender and recipient from predefined constants, and sends the 
    email through a predefined SMTP server. If sending fails, it logs the error.

    Args:
        formatted_email_body (str): The body of the email to be sent.

    Returns:
        True or None

    Raises:
        smtplib.SMTPException: An error occurred during the email sending process.
    """
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_FROM_KEY)
            msg = MIMEMultipart()
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO
            msg["Subject"] = "Lightrail status alert"
            msg.attach(MIMEText("===\n".join(formatted_email_body), "plain"))
            server.send_message(msg)
            logging.info("Email sent successfully!")
            return True
    except smtplib.SMTPException as e:
        logging.error(f"An error occurred while sending email: {e}")
        return None


def main(gcp_arg):
    """The main function that orchestrates the process of fetching data from the API, 
    processing it, checking for new alerts, logging them into BigQuery, and sending 
    email notifications.

    Args:
        gcp_arg (str): A string argument typically used for logging or configuration, 
        which is specific to Google Cloud Platform (GCP) services.

    Returns:
        tuple: A tuple containing a message string and an HTTP status code. On successful
            completion, it returns ("Complete.", 200). If any step fails, it returns an error
            message and a 500 status code indicating an internal server error.
    """
    logging.info(gcp_arg)
    response_json = fetch_data()
    if response_json is None:
        logging.error("No response received from the API.")
        return ("Error: The API response is invalid", 500)
    logging.info(f"Response: {response_json}\n=====")

    number_of_results = len(response_json["entity"])
    logging.info(f"found {number_of_results}")

    client = bigquery_interface.create_bq_client()
    if not bigquery_interface.check_table_exists(client):
        bigquery_interface.create_new_table(client)

    alerts_to_email = []
    for idx, entity in enumerate(response_json["entity"]):
        processed_response_alert = process_response_alert(entity)
        if processed_response_alert is None:
            return (f"Error: Unable to process result {entity}", 500)
        logging.info(f"result: {idx+1}. remaining: {number_of_results - idx}")
        logging.info(f"\n{processed_response_alert}\n")

        if processed_response_alert[
            "l1_line_impacted"
        ] == True and not bigquery_interface.check_alert_id_is_unique(
            client, processed_response_alert
        ):
            logging.info("New alert found.")
            bigquery_interface.insert_values_into_table(client, processed_response_alert)
            alerts_to_email.append(processed_response_alert)
        else:
            logging.info("Skipping alert.")

    logging.info(f"Alerts:\n{alerts_to_email}")
    if len(alerts_to_email) > 0:
        email_body_content = []
        for alert in alerts_to_email:
            email_body_content.append(format_email_body(alert))

        logging.info("Sending email")
        send_email_result = send_email(email_body_content)
        if send_email_result is None:
            return ("Error: Unable to send email.", 500)
    else:
        logging.info("No new alerts found")

    logging.info("Process complete.")
    return ("Complete.", 200)


if __name__ == "__main__":
    main("Running locally.")
