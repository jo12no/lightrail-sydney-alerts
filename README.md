# lightrail-sydney-alerts 🚃
This project uses the TNSW API to check for Sydney Lightrail 1) service status alerts and 2) timetable changes for a specified time. An email is sent as a push notification on new events. 

This means I no longer need to check anything relating to transport before commuting to or from the office (which is helpful given reliability issues!)

## Technical Infrastructure 


* For `lightrail_timetable_alert.py` which simply checks whether the train is still scheduled to leave a specified time, there's no need to save results in a BigQuery table to check for uniqueness. 

## Example Notifications  

## Description 
The script operates as a monitoring tool for Sydney Lightrail line alerts by interacting with the Transport for New South Wales (TNSW) API. It performs several key functions:

Data Fetching: It retrieves alert data from the TNSW API specifically for the Sydney Lightrail lines.

Alert Processing: The script processes the fetched alert data to extract and format relevant information like the alert's ID, URL, title, description, and start/end dates. It also checks if the L1 line is impacted. This is saved to BigQuery as an `alert`. 

BigQuery Integration: It compares the processed alerts against existing records in a BigQuery table to determine if they are new.

Email Notifications: If an alert is new (not already in the BigQuery table), it formats the alert details into an email body and sends an email notification to a pre-configured recipient.

Scheduling and Hosting: Designed to be hosted as a serverless Cloud Function, the script is intended to execute every minute.

## Getting Started
* This is provided primarily for reference/demo purposes, however you can modify the `config.py` settings with your email, Cloud project and relevant Lightrail details. 
* Install required libraries using `pip install -r requirements.txt`.
* Run the script using either `python lightrail_service_status_alert.py` or `python lightrail_timetable_alert.py`.
* Optionally deploy to a serverless Cloud solution to schedule. 

## Considerations
* I use a separate 'bot' email account to send the emails to my personal account which improves security. 
