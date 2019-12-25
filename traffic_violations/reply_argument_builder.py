import logging
import pytz
import re

from datetime import datetime, timezone
from typing import Type

from traffic_violations.constants.lookup_sources import LookupSources
from traffic_violations.constants.twitter import TwitterAPIAttributes, \
    TwitterMessageTypes

from traffic_violations.models.lookup_requests import BaseLookupRequest, \
    AccountActivityAPIDirectMessage, AccountActivityAPIStatus, \
    DirectMessageAPIDirectMessage,  HowsMyDrivingAPIRequest, SearchStatus, \
    StreamExtendedStatus, StreamingDirectMessage, StreamingStatus

LOG = logging.getLogger(__name__)


class ReplyArgumentBuilder:

    def __init__(self, api):
        self.api = api

    def build_reply_data(self, message, message_source, message_type):

        LOG.info(
            f'args for reply data:'
            f'message: {message}'
            f'message_source: {message_source}'
            f'message_type: {message_type}')

        lookup_request: Type[BaseLookupRequest] = None

        # why doesn't python have switch statements
        if message_source == LookupSources.TWITTER:

            if message_type == TwitterMessageTypes.STATUS:

                # Using old streaming service for a tweet longer than 140
                # characters

                if hasattr(message, TwitterAPIAttributes.EXTENDED_TWEET.value):
                    LOG.debug('We have an extended tweet')

                    lookup_request = StreamExtendedStatus(
                        message, message_source, message_type)

                # Using tweet api search endpoint

                elif hasattr(message, TwitterAPIAttributes.FULL_TEXT.value) and (not hasattr(message, TwitterAPIAttributes.RETWEETED_STATUS.value)):
                    LOG.debug(
                        'We have a tweet from the search api endpoint')

                    lookup_request = SearchStatus(
                        message, message_source, message_type)

                # Using old streaming service for a tweet of 140 characters or
                # fewer

                elif hasattr(message, TwitterAPIAttributes.ENTITIES.value) and (not hasattr(message, TwitterAPIAttributes.RETWEETED_STATUS.value)):

                    LOG.debug(
                        'We are dealing with a tweet of '
                        '140 characters or fewer')

                    lookup_request = StreamingStatus(
                        message, message_source, message_type)

                # Using new account api service by way of SQL table for events

                elif type(message) == dict and TwitterAPIAttributes.EVENT_TYPE.value in message:

                    LOG.debug(
                        'We are dealing with account activity api object')

                    lookup_request = AccountActivityAPIStatus(
                        message, message_source, message_type)

            elif message_type == TwitterMessageTypes.DIRECT_MESSAGE:

                # Using old streaming service for a direct message
                if hasattr(message, TwitterAPIAttributes.DIRECT_MESSAGE.value):

                    LOG.debug(
                        'We have a direct message from the streaming service')

                    lookup_request = StreamingDirectMessage(
                        message, message_source, message_type)

                # Using new direct message api endpoint

                elif hasattr(message, TwitterAPIAttributes.MESSAGE_CREATE.value):

                    LOG.debug(
                        'We have a direct message from the direct message api')

                    lookup_request = DirectMessageAPIDirectMessage(
                        message, message_source, message_type, self.api)

                # Using account activity api endpoint

                elif TwitterAPIAttributes.EVENT_TYPE.value in message:

                    LOG.debug(
                        'We are dealing with an account activity api object')

                    lookup_request = AccountActivityAPIDirectMessage(
                        message, message_source, message_type)

        elif message_source == LookupSources.API:

            LOG.debug(
                'We are dealing with a HowsMyDrivingNY API request')

            lookup_request = HowsMyDrivingAPIRequest(
                message, message_source, message_type)

        else:

            LOG.debug('Unrecognized request type')

            lookup_request = BaseLookupRequest(None, 'unknown', 'unknown')

        return lookup_request
