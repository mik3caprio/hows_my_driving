import mock
import os
import pytz
import random
import statistics
import unittest

from datetime import datetime, timezone, time, timedelta

from unittest.mock import call, MagicMock

from traffic_violations.models.twitter_event import TwitterEvent

from traffic_violations.reply_argument_builder import \
    AccountActivityAPIDirectMessage, AccountActivityAPIStatus

from traffic_violations.services.twitter_service import \
    TrafficViolationsTweeter


def inc(part, in_reply_to_status_id):
    int_mock = MagicMock(name='api')
    int_mock.id = (in_reply_to_status_id + 1)
    return int_mock


class TestTrafficViolationsTweeter(unittest.TestCase):

    def setUp(self):
        self.tweeter = TrafficViolationsTweeter()

    def test_find_messages_to_respond_to(self):
        twitter_events_mock = MagicMock(
            name='find_and_respond_to_twitter_events')
        self.tweeter._find_and_respond_to_twitter_events = twitter_events_mock

        self.tweeter._find_messages_to_respond_to()

        twitter_events_mock.assert_called_with()

    @mock.patch(
        'traffic_violations.services.twitter_service.TwitterEvent')
    def test_find_and_respond_to_twitter_events(self, twitter_event_mock):
        db_id = 1
        random_id = random.randint(10000000000000000000, 20000000000000000000)
        event_type = 'status'
        user_handle = 'bdhowald'
        user_id = random.randint(1000000000, 2000000000)
        event_text = '@HowsMyDrivingNY abc1234:ny'
        timestamp = random.randint(1500000000000, 1700000000000)
        in_reply_to_message_id = random.randint(
            10000000000000000000, 20000000000000000000)
        location = 'Queens, NY'
        responded_to = 0
        user_mentions = '@HowsMyDrivingNY'

        twitter_event = TwitterEvent(
            id=db_id,
            created_at=timestamp,
            event_id=random_id,
            event_text=event_text,
            event_type=event_type,
            in_reply_to_message_id=in_reply_to_message_id,
            location=location,
            responded_to=responded_to,
            user_handle=user_handle,
            user_id=user_id,
            user_mentions=user_mentions)

        lookup_request = AccountActivityAPIDirectMessage(
            message=TwitterEvent(
                id=1,
                created_at=timestamp,
                event_id=random_id,
                event_text='@howsmydrivingny ny:hme6483',
                event_type='direct_message',
                user_handle=user_handle,
                user_id=30139847),
            message_source='api')

        twitter_event_mock.get_all_by.return_value = [twitter_event]
        twitter_event_mock.query.filter_by().filter().count.return_value = 0

        initiate_reply_mock = MagicMock(name='initiate_reply')
        self.tweeter.aggregator.initiate_reply = initiate_reply_mock

        build_reply_data_mock = MagicMock(name='build_reply_data')
        build_reply_data_mock.return_value = lookup_request
        self.tweeter.reply_argument_builder.build_reply_data = build_reply_data_mock

        self.tweeter._find_and_respond_to_twitter_events()

        self.tweeter.aggregator.initiate_reply.assert_called_with(
            lookup_request=lookup_request)

    def test_is_production(self):
        self.assertEqual(self.tweeter._is_production(),
                         (os.environ.get('ENV') == 'production'))

    @mock.patch(
        'traffic_violations.services.twitter_service.TrafficViolationsTweeter._is_production')
    def test_process_response_direct_message(self, mocked_is_production):
        """ Test direct message and new format """

        username = 'bdhowald'
        message_id = random.randint(1000000000000000000, 2000000000000000000)

        lookup_request = AccountActivityAPIDirectMessage(
            message=TwitterEvent(
                id=1,
                created_at=random.randint(1_000_000_000_000, 2_000_000_000_000),
                event_id=message_id,
                event_text='@howsmydrivingny ny:hme6483',
                event_type='direct_message',
                user_handle=username,
                user_id=30139847),
            message_source='direct_message')

        combined_message = "@bdhowald #NY_HME6483 has been queried 1 time.\n\nTotal parking and camera violation tickets: 15\n\n4 | No Standing - Day/Time Limits\n3 | No Parking - Street Cleaning\n1 | Failure To Display Meter Receipt\n1 | No Violation Description Available\n1 | Bus Lane Violation\n\n@bdhowald Parking and camera violation tickets for #NY_HME6483, cont'd:\n\n1 | Failure To Stop At Red Light\n1 | No Standing - Commercial Meter Zone\n1 | Expired Meter\n1 | Double Parking\n1 | No Angle Parking\n\n@bdhowald Violations by year for #NY_HME6483:\n\n10 | 2017\n15 | 2018\n\n@bdhowald Known fines for #NY_HME6483:\n\n$200.00 | Fined\n$125.00 | Outstanding\n$75.00   | Paid\n"

        reply_event_args = {
            'error_on_lookup': False,
            'request_object': lookup_request,
            'response_parts': [[combined_message]],
            'success': True,
            'successful_lookup': True,
            'username': username
        }

        mocked_is_production.return_value = True

        send_direct_message_mock = MagicMock('send_direct_message_mock')

        api_mock = MagicMock(name='api')
        api_mock.send_direct_message = send_direct_message_mock

        self.tweeter.api = api_mock

        self.tweeter._process_response(reply_event_args)

        send_direct_message_mock.assert_called_with(
          recipient_id=30139847,
          text=combined_message)

    @mock.patch(
        'traffic_violations.services.twitter_service.TrafficViolationsTweeter._recursively_process_status_updates')
    def test_process_response_status_legacy_format(self,
                                                   recursively_process_status_updates_mock):
        """ Test status and old format """

        username = 'BarackObama'
        message_id = random.randint(1000000000000000000, 2000000000000000000)

        response_parts = [['@BarackObama #PA_GLF7467 has been queried 1 time.\n\nTotal parking and camera violation tickets: 49\n\n17 | No Parking - Street Cleaning\n6   | Expired Meter\n5   | No Violation Description Available\n3   | Fire Hydrant\n3   | No Parking - Day/Time Limits\n', "@BarackObama Parking and camera violation tickets for #PA_GLF7467, cont'd:\n\n3   | Failure To Display Meter Receipt\n3   | School Zone Speed Camera Violation\n2   | No Parking - Except Authorized Vehicles\n2   | Bus Lane Violation\n1   | Failure To Stop At Red Light\n",
                           "@BarackObama Parking and camera violation tickets for #PA_GLF7467, cont'd:\n\n1   | No Standing - Day/Time Limits\n1   | No Standing - Except Authorized Vehicle\n1   | Obstructing Traffic Or Intersection\n1   | Double Parking\n", '@BarackObama Known fines for #PA_GLF7467:\n\n$1,000.00 | Fined\n$225.00     | Outstanding\n$775.00     | Paid\n']]

        lookup_request = AccountActivityAPIStatus(
            message=TwitterEvent(
                id=1,
                created_at=random.randint(1_000_000_000_000, 2_000_000_000_000),
                event_id=message_id,
                event_text='@howsmydrivingny plate:glf7467 state:pa',
                event_type='status',
                user_handle=username,
                user_id=30139847),
            message_source='status')

        reply_event_args = {
            'error_on_lookup': False,
            'request_object': lookup_request,
            'response_parts': response_parts,
            'success': True,
            'successful_lookup': True,
            'username': username
        }

        is_production_mock = MagicMock(name='is_production')
        is_production_mock.return_value = True

        create_favorite_mock = MagicMock(name='is_production')
        create_favorite_mock.return_value = True

        api_mock = MagicMock(name='api')
        api_mock.create_favorite = create_favorite_mock

        self.tweeter._is_production = is_production_mock
        self.tweeter.api = api_mock

        reply_event_args['username'] = username

        self.tweeter._process_response(reply_event_args)

        recursively_process_status_updates_mock.assert_called_with(
            response_parts, message_id, username)

    @mock.patch(
        'traffic_violations.services.twitter_service.TrafficViolationsTweeter._recursively_process_status_updates')
    def test_process_response_campaign_only_lookup(self,
                                                   recursively_process_status_updates_mock):
        """ Test campaign-only lookup """

        username = 'NYCMayorsOffice'
        message_id = random.randint(1000000000000000000, 2000000000000000000)
        campaign_hashtag = '#SaferSkillman'
        campaign_tickets = random.randint(1000, 2000)
        campaign_vehicles = random.randint(100, 200)

        response_parts = [['@' + username + ' ' + str(campaign_vehicles) + ' vehicles with a total of ' + str(
            campaign_tickets) + ' tickets have been tagged with ' + campaign_hashtag + '.\n\n']]

        lookup_request = AccountActivityAPIStatus(
            message=TwitterEvent(
                id=1,
                created_at=random.randint(1_000_000_000_000, 2_000_000_000_000),
                event_id=message_id,
                event_text=f'@howsmydrivingny {campaign_hashtag}',
                event_type='status',
                user_handle=username,
                user_id=30139847),
            message_source='status')

        reply_event_args = {
            'error_on_lookup': False,
            'request_object': lookup_request,
            'response_parts': response_parts,
            'success': True,
            'successful_lookup': True,
            'username': username
        }

        reply_event_args['username'] = username

        self.tweeter._process_response(reply_event_args)

        recursively_process_status_updates_mock.assert_called_with(
            response_parts, message_id, username)

    @mock.patch(
        'traffic_violations.services.twitter_service.TrafficViolationsTweeter._recursively_process_status_updates')
    def test_process_response_with_search_status(self,
                                                 recursively_process_status_updates_mock):
        """ Test plateless lookup """

        username = 'NYC_DOT'
        message_id = random.randint(1000000000000000000, 2000000000000000000)

        response_parts = [
            ['@' + username + ' I’d be happy to look that up for you!\n\nJust a reminder, the format is <state|province|territory>:<plate>, e.g. NY:abc1234']]

        lookup_request = AccountActivityAPIStatus(
            message=TwitterEvent(
                id=1,
                created_at=random.randint(1_000_000_000_000, 2_000_000_000_000),
                event_id=message_id,
                event_text='@howsmydrivingny plate dkr9364 state ny',
                event_type='status',
                user_handle=username,
                user_id=30139847),
            message_source='status')

        reply_event_args = {
            'error_on_lookup': False,
            'request_object': lookup_request,
            'response_parts': response_parts,
            'success': True,
            'successful_lookup': True,
            'username': username
        }

        reply_event_args['username'] = username

        self.tweeter._process_response(reply_event_args)

        recursively_process_status_updates_mock.assert_called_with(
            response_parts, message_id, username)

    @mock.patch(
        'traffic_violations.services.twitter_service.TrafficViolationsTweeter._recursively_process_status_updates')
    def test_process_response_with_direct_message_api_direct_message(self,
                                                                     recursively_process_status_updates_mock):
        """ Test plateless lookup """

        username = 'NYCDDC'
        message_id = random.randint(1000000000000000000, 2000000000000000000)

        response_parts = [
            ['@' + username + " I think you're trying to look up a plate, but can't be sure.\n\nJust a reminder, the format is <state|province|territory>:<plate>, e.g. NY:abc1234"]]

        lookup_request = AccountActivityAPIStatus(
            message=TwitterEvent(
                id=1,
                created_at=random.randint(1_000_000_000_000, 2_000_000_000_000),
                event_id=message_id,
                event_text='@howsmydrivingny the state is ny',
                event_type='status',
                user_handle=username,
                user_id=30139847),
            message_source='status')

        reply_event_args = {
            'error_on_lookup': False,
            'request_object': lookup_request,
            'response_parts': response_parts,
            'success': True,
            'successful_lookup': True,
            'username': username
        }

        reply_event_args['username'] = username

        self.tweeter._process_response(reply_event_args)

        recursively_process_status_updates_mock.assert_called_with(
            response_parts, message_id, username)

    @mock.patch(
        'traffic_violations.services.twitter_service.TrafficViolationsTweeter._recursively_process_status_updates')
    def test_process_response_with_error(self,
                                         recursively_process_status_updates_mock):
        """ Test error handling """

        username = 'BarackObama'
        message_id = random.randint(1000000000000000000, 2000000000000000000)

        lookup_request = AccountActivityAPIStatus(
            message=TwitterEvent(
                id=1,
                created_at=random.randint(1_000_000_000_000, 2_000_000_000_000),
                event_id=message_id,
                event_text='@howsmydrivingny plate:glf7467 state:pa',
                event_type='status',
                user_handle=username,
                user_id=30139847),
            message_source='status'
        )

        response_parts = [
            ['@' + username + " Sorry, I encountered an error. Tagging @bdhowald."]]

        reply_event_args = {
            'error_on_lookup': False,
            'request_object': lookup_request,
            'response_parts': response_parts,
            'success': True,
            'successful_lookup': True,
            'username': username
        }

        reply_event_args['username'] = username

        self.tweeter._process_response(reply_event_args)

        recursively_process_status_updates_mock.assert_called_with(
            response_parts, message_id, username)

    def test_recursively_process_direct_messages(self):
        str1 = 'Some stuff\n'
        str2 = 'Some other stuff\nSome more Stuff'
        str3 = 'Yet more stuff'

        response_parts = [
            [str1], str2, str3
        ]

        result_str = "\n".join([str1, str2, str3])

        self.assertEqual(self.tweeter._recursively_process_direct_messages(
            response_parts), result_str)

    def test_recursively_process_status_updates(self):
        str1 = 'Some stuff\n'
        str2 = 'Some other stuff\nSome more Stuff'
        str3 = 'Yet more stuff'

        original_id = 1

        response_parts = [
            [str1], str2, str3
        ]

        api_mock = MagicMock(name='api')
        api_mock.update_status = inc

        is_production_mock = MagicMock(name='is_production')
        is_production_mock.return_value = True

        self.tweeter.api = api_mock
        self.tweeter._is_production = is_production_mock

        self.assertEqual(self.tweeter._recursively_process_status_updates(
            response_parts, original_id, 'BarackObama'), original_id + len(response_parts))

        self.assertEqual(self.tweeter._recursively_process_status_updates(
            response_parts, original_id, 'BarackObama'), original_id + len(response_parts))