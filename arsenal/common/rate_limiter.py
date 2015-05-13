# -*- encoding: utf-8 -*-
#
# Copyright 2015 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime


# NOTE(ClifHouck): Wrapper function for datetime.now() to make it mockable.
def now():
    return datetime.datetime.now()


class RateLimiter(object):
    """This class provides rate-limiting behavior."""

    def __init__(self, limit, limit_period):
        """Constructs a RateLimiter object.

            :param: limit - An integral limit to observe. Once the limit is
                hit, no more items will be returned until the current
                limit_period expires.
            :param: limit_period - Integral time in seconds. The period in
                which withdrawing items counts towards the current period's
                rate limit.
            :returns: A RateLimiter object.
        """
        if not isinstance(limit, int):
            raise TypeError("limit must be an integer, wrong type received")
        if not isinstance(limit_period, int):
            raise TypeError("limit_period must be an integer, "
                            "wrong type received")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        if limit_period <= 0:
            raise ValueError("limit_period must be a positive integer")

        self.limit = limit
        self.limit_period = limit_period
        self.limit_period_delta = datetime.timedelta(days=0,
                                                     seconds=limit_period)
        self.current_limit_period_start = now()
        self.current_count = 0
        self.items = []

    def _start_new_limit_period(self):
        self.current_limit_period_start = now()
        self.current_count = 0

    def _update_limit_period(self):
        delta = now() - self.current_limit_period_start
        if delta >= self.limit_period_delta:
            self._start_new_limit_period()

    def __len__(self):
        return len(self.items)

    def clear(self):
        self.items = []

    def add_items(self, iterable):
        """Adds items to the queue."""
        self.items.extend(iterable)

    def withdraw_items(self):
        """Returns a number of items from the RateLimiter.

        If the number items withdrawn would exceed the limit for the
        current limiting period, then this function will return the maximum
        number of items possible without violating the limit. Returns the
        empty list if the current limit has already been reached, or
        there are no more items to return.
        """
        self._update_limit_period()

        if self.current_count >= self.limit or len(self.items) == 0:
            outbound_items = []
        elif (len(self.items) + self.current_count) > self.limit:
            num_items_to_return = self.limit - self.current_count
            outbound_items = self.items[0:num_items_to_return]
            self.current_count += num_items_to_return
            self.items = self.items[num_items_to_return:]
        else:
            outbound_items = self.items
            self.current_count += len(outbound_items)
            self.items = []
        return outbound_items
