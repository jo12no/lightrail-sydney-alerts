# lightrail-sydney-alerts 🚃
This project integrates with the Transport for New South Wales (TfNSW) API to monitor the Sydney Light Rail network for:
1) Service status alerts via `lightrail_service_status_alert.py`, and 
2) Timetable modifications for specified times through `lightrail_timetable_alert.py`.

Whenever new events are detected, an email is automatically sent as a push notification.

This means I no longer need to manually check anything before commuting to or from the office (which is helpful given recent reliability issues!!)

## Technical Infrastructure 
![Example](https://github.com/jo12no/lightrail-sydney-alerts/assets/19522573/54ff096a-902e-4fce-8c3b-3923377c1ada)
* For `lightrail_timetable_alert.py` which simply checks whether the train is still scheduled to leave at a specified time, there's no need to save results in a BigQuery table to check for uniqueness. 

## Example Output Notifications  
![Output2](https://github.com/jo12no/lightrail-sydney-alerts/assets/19522573/819841a1-8ba7-475b-aed3-7c4ddc42786c)

![Output1](https://github.com/jo12no/lightrail-sydney-alerts/assets/19522573/bc4782cf-f1b6-47fa-aa04-a4a5e18c42a7)


<sup>_* Images obfuscated for privacy._</sup>

## Description 
The script operates as a monitoring tool for Sydney Lightrail line alerts by interacting with the Transport for New South Wales (TNSW) API. It performs several key functions:

Data Fetching: It retrieves alert data from the TNSW API specifically for the Sydney Lightrail lines.

Alert Processing: The script processes the fetched alert data to extract and format relevant information like the alert's ID, URL, title, description, and start/end dates. It also checks if the L1 line is impacted. This is saved to BigQuery as an `alert`. 

BigQuery Integration: It compares the processed alerts against existing records in a BigQuery table to determine if they are new.

Email Processing: If an alert is new (not already in the BigQuery table), it formats the alert details into an email body.

Email Sending (SMTP protocol): the email is sent from a service 'bot' email account, which emails my personal account. 

Scheduling and Hosting: Designed to be hosted as a serverless Cloud Function, the script is intended to execute every minute.

## Getting Started
* This is provided primarily for reference/demo purposes, however you can modify the `config.py` settings with your email, Cloud project and relevant Lightrail details. 
* Install required libraries using `pip install -r requirements.txt`.
* Run the script using either `python lightrail_service_status_alert.py` or `python lightrail_timetable_alert.py`.
* Optionally deploy to a serverless Cloud solution to schedule. 

## Considerations
* I use a separate 'bot' email account to send the emails to my personal account which improves security. 
