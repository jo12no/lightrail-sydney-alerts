"""Check if the specified lightrail depature is occuring that day.

Intended to be hosted in Google Cloud Platform as a Cloud Function and scheduled to run
daily prior to the depature time to check against. 
"""
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config
import pytz
import requests

# Settings (anonymised)
TARGET_DEPARTURE_HOUR = 7
TARGET_DEPARTURE_MINUTES = 50
STATION_ID = 220322

# Set the logging level to INFO so that INFO messages get logged.
# pylint: disable=W1203
logging.basicConfig(level=logging.INFO)

# API Constants
API_URL = "https://api.transport.nsw.gov.au/v1/tp/departure_mon?outputFormat=rapidJSON&departureMonitorMacro=true&TfNSWDM=true"
TNSW_API_KEY = config.TNSW_API_KEY if config.TNSW_API_KEY else os.getenv("TNSW_API_KEY")
# Email Configuration
EMAIL_BODY = f"No {TARGET_DEPARTURE_HOUR}:{TARGET_DEPARTURE_MINUTES} depature found: https://transportnsw.info/trip#/departures?accessible=false&depart=220322&routes=780l1&type=stop"
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
EMAIL_FROM = config.EMAIL_FROM
EMAIL_TO = config.EMAIL_TO
EMAIL_FROM_KEY = config.EMAIL_FROM_KEY


def fetch_data():
    """Retrieves departure data from a transport API for a specified station.

    The function sends an HTTP GET request to the transport API using predefined
    API URL, headers, and parameters. By default, it retrieves departures based on
    the current server time. It can be customized with specific date and time by
    providing 'itdDate' and 'itdTime' in the parameters. If the request is successful,
    it returns the response in JSON format. In case of a network or HTTP error,
    the error is logged, and None is returned.

    Returns:
        dict or None: A dictionary containing the fetched data if the request is
                      successful, or None if an exception occurs.

    Raises:
        requests.RequestException: An error occurred while making the HTTP request.
    """
    headers = {"Authorization": f"apikey {TNSW_API_KEY}"}
    params = {
        "name_dm": STATION_ID,
        "type_dm": "stop",
        "mode": "direct",
        "excludedMeans": "checkbox",
        "exclMOT_1": "1",
        "exclMOT_2": "1",
        "exclMOT_5": "1",
        "exclMOT_7": "1",
        "exclMOT_9": "1",
        "exclMOT_11": "1",
    }
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"An error occurred while fetching data: {e}")
        return None


def format_target_time():
    """Formats the target departure time accounting for Sydney's daylight savings.

    This function sets a fixed departure time for the current date in Sydney timezone
    and converts it to UTC. It is set to account for any changes due to daylight
    savings automatically.

    Returns:
        str: The target time formatted as "HH:MM" in UTC.
    """
    sydney_tz = pytz.timezone("Australia/Sydney")
    # Specify 7:40 AM for today's date in Sydney - this is the depature time to verify
    specified_sydney_datetime = datetime.now().replace(
        hour=TARGET_DEPARTURE_HOUR, minute=TARGET_DEPARTURE_MINUTES
    )
    localized_sydney_datetime = sydney_tz.localize(specified_sydney_datetime)
    # Convert the specified Sydney time to UTC
    utc_time = localized_sydney_datetime.astimezone(pytz.utc)
    return utc_time.strftime("%H:%M")  # 07:40 Syd is 20:40 UTC


def send_email(formatted_email_body):
    """Sends an email with a given body to a predefined recipient.

    This function constructs an email message using the `formatted_email_body` parameter,
    sets the sender and recipient from predefined constants, and sends the email through
    a predefined SMTP server. If sending fails, it logs the error.

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
            msg["Subject"] = "Lightrail timetable alert"
            msg.attach(MIMEText(formatted_email_body, "plain"))
            server.send_message(msg)
            logging.info("Email sent successfully!")
            return True
    except smtplib.SMTPException as e:
        logging.error(f"An error occurred while sending email: {e}")
        return None


def main(gcp_arg):
    """Main execution function that processes departure data and sends an email alert 
    if a target time is not found.

    This function logs the provided Google Cloud Platform (GCP) argument, fetches 
    departure data using the `fetch_data` function, and checks for the presence of a 
    target departure time within the response. If the target time is not
    found in the departure data, it triggers an email alert by calling `send_email`. 
    It returns a tuple with a message and an HTTP status code indicating the result 
    of the operation.

    Args:
        gcp_arg (str): A string argument typically used for passing GCP-related 
        information.

    Returns:
        tuple: A two-element tuple consisting of a string message and an HTTP status 
        code.
        For example: ("Error: The API response is invalid", 500) or ("Complete.", 200)

    Raises:
        ValueError: If `gcp_arg` is not valid or in an unexpected format.
    """
    logging.info(gcp_arg)
    response_json = fetch_data()
    if response_json is None:
        logging.error("No response received from the API.")
        return ("Error: The API response is invalid", 500)
    logging.info(response_json)
    target_time = format_target_time()
    logging.info(
        f"\nSydney Time: {TARGET_DEPARTURE_HOUR}:{TARGET_DEPARTURE_MINUTES}. UTC Target time: {target_time}."
    )

    found_target_time = False
    for idx, x in enumerate(response_json["stopEvents"]):
        logging.info(f"count: {idx}. {x['departureTimePlanned']}")
        if target_time in x["departureTimePlanned"]:
            found_target_time = True
            logging.info("found target time in planned departures - no email to send")
            break

    if not found_target_time:
        logging.info("no matching depature time was found! sending email to alert")
        send_email_result = send_email(EMAIL_BODY)
        if send_email_result is None:
            return ("Error: Unable to send email.", 500)

    logging.info('Process complete.')
    return ("Complete.", 200)


if __name__ == "__main__":
    main("Running locally.")
