from calendly_helpers import *
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--code', '-c', dest='code')
parser.add_argument('--token', '-t', dest='access_token')
parser.add_argument('--employees', '-e',
                    dest='with_employee', action='store_false')
args = parser.parse_args()


access_token = refresh_access_token()
# if args.access_token:
#     access_token = args.access_token
# else:
#     if args.code:
#         code = args.code
#     else:
#         print(url_for_code())
#         code = input("Provide Code: ")

#     access_token = retreive_access_token(code=code, ttl_hash=get_ttl_hash())

print("Retreiving Scheduled Events")
scheduled_events = get_scheduled_events(access_token=access_token)
scheduled_events['start_time'] = pd.to_datetime(
    scheduled_events['start_time']).dt.tz_convert('US/Eastern')
scheduled_events['end_time'] = pd.to_datetime(
    scheduled_events['end_time']).dt.tz_convert('US/Eastern')
scheduled_events['created_at'] = pd.to_datetime(
    scheduled_events['created_at']).dt.tz_convert('US/Eastern')

# upcoming_events = scheduled_events[(
#     scheduled_events.status != 'canceled')].sort_values('start_time')
upcoming_events = scheduled_events[(scheduled_events.start_time >= yesterday_str()) & (
    scheduled_events.status != 'canceled')].sort_values('start_time')

print("Output events to",
      'data/upcoming_events_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))
upcoming_events.to_csv(
    'data/upcoming_events_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))

invitees = get_invitee_details(upcoming_events, access_token)
invitees = invitees[['EmpNum', 'name', 'event',
                     'email', 'working_after_vaccine', 'contact_number', 'uri', 'created_at', 'status']]
# active only
invitees = invitees[invitees['status'] == 'active']
invitees.columns = ['EmpNum', 'EmployeeName', 'event',
                    'email', 'working_after_vaccine', 'contact_number', 'invitee_event_uri', 'created_at', 'status']

event_roster = upcoming_events[['name', 'start_time', 'uri']].merge(
    invitees, how='left', left_on='uri', right_on='event')

check_in_view = event_roster[['name', 'start_time', 'end_time',
                              'EmpNum', 'EmployeeName', 'email', 'contact_number', 'created_at']]
# Create date and time columns
check_in_view['start_date'] = check_in_view.start_time.dt.date
check_in_view.start_time = check_in_view.start_time.dt.time

print("Output roster to",
      'data/upcoming_events_with_invitees_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))
event_roster.to_csv(
    'data/upcoming_events_with_invitees_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))


print("Output invitees to",
      'data/invitees_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))
invitees.to_csv(
    'data/invitees_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))


print("Output check_in_view to",
      'data/checkinview_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))
check_in_view.to_csv(
    'data/checkinview_{}.csv'.format(today_str(fmt="%Y-%m-%d_%H%M")))
