# Copyright 2015 Rackspace.
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

import mock

from arsenal.common import rate_limiter
from arsenal.tests import base as test_base

FIVE_SECONDS = datetime.timedelta(0, 5)
ONE_SECOND = datetime.timedelta(0, 1)
START_DATETIME = datetime.datetime(2015, 1, 1, 0, 0, 0)
PAST_DATETIME = datetime.datetime(2014, 7, 30, 0, 0, 0)


class RateLimiterTestCase(test_base.TestCase):

    def setUp(self):
        super(RateLimiterTestCase, self).setUp()

    @mock.patch('arsenal.common.rate_limiter.now')
    def test_update_limit_period(self, now_mock):
        now_mock.return_value = START_DATETIME
        rl_obj = rate_limiter.RateLimiter(10, 5)
        self.assertEqual(START_DATETIME, rl_obj.current_limit_period_start)

        now_mock.return_value = START_DATETIME + ONE_SECOND
        rl_obj.current_count = 3
        rl_obj._update_limit_period()
        # These shouldn't change yet.
        self.assertEqual(START_DATETIME,
                         rl_obj.current_limit_period_start)
        self.assertEqual(3, rl_obj.current_count)

        # Now we're beyond the initial period, and the rate limiter should
        # create a new period starting when withdraw_items() is called, and
        # reset the count.
        now_mock.return_value = START_DATETIME + FIVE_SECONDS
        rl_obj.current_count = 3
        rl_obj._update_limit_period()
        self.assertEqual(START_DATETIME + FIVE_SECONDS,
                         rl_obj.current_limit_period_start)
        self.assertEqual(0, rl_obj.current_count)

    def test_adding_items(self):
        rl_obj = rate_limiter.RateLimiter(3, 10)
        rl_obj.add_items(range(0, 10))
        self.assertEqual(10, len(rl_obj))
        rl_obj.add_items(range(0, 10))
        self.assertEqual(20, len(rl_obj))

    @mock.patch('arsenal.common.rate_limiter.now')
    def test_withdraw_rate_limiting(self, now_mock):
        now_mock.return_value = START_DATETIME
        item_limit = 10
        rl_obj = rate_limiter.RateLimiter(item_limit, 5)
        rl_obj.add_items(range(0, 105))

        # We should've gotten the first ten items back.
        return_list = rl_obj.withdraw_items()
        self.assertEqual(range(0, 10), return_list)
        self.assertEqual(95, len(rl_obj))

        # Now we should only get the empty list back.
        for n in range(0, 3):
            return_list = rl_obj.withdraw_items()
            self.assertEqual([], return_list)
            self.assertEqual(95, len(rl_obj))

        item_count = 95
        item_start = 10
        item_end = 20
        # Pump items out of the rate limiter.
        for i in range(0, 9):
            rl_obj._start_new_limit_period()
            return_list = rl_obj.withdraw_items()
            item_count -= item_limit
            self.assertEqual(range(item_start, item_end), return_list)
            self.assertEqual(item_count, len(rl_obj))
            item_start += item_limit
            item_end += item_limit

        # Now we should only get 5 back.
        rl_obj._start_new_limit_period()
        return_list = rl_obj.withdraw_items()
        self.assertEqual(range(100, 105), return_list)
        self.assertEqual(0, len(rl_obj))
        self.assertEqual(5, rl_obj.current_count)

    def test_init_arguments(self):
        # Test some cases that should raise
        self.assertRaises(TypeError, rate_limiter.RateLimiter, 10, "dog")
        self.assertRaises(TypeError, rate_limiter.RateLimiter, "cat", 1)
        self.assertRaises(ValueError, rate_limiter.RateLimiter, 10, 0)
        self.assertRaises(ValueError, rate_limiter.RateLimiter, 0, 5)
        self.assertRaises(ValueError, rate_limiter.RateLimiter, 10, -5)
        self.assertRaises(ValueError, rate_limiter.RateLimiter, -5, 5)
        # And some that should be OK
        self.assertIsInstance(rate_limiter.RateLimiter(1, 2),
                              rate_limiter.RateLimiter)
        self.assertIsInstance(rate_limiter.RateLimiter(3, 4),
                              rate_limiter.RateLimiter)
        self.assertIsInstance(rate_limiter.RateLimiter(10000, 1000000),
                              rate_limiter.RateLimiter)

    @mock.patch('arsenal.common.rate_limiter.now')
    @mock.patch.object(rate_limiter.RateLimiter, '_start_new_limit_period')
    def test_time_went_backwards(self, new_limit_period_mock, now_mock):
        """Make certain that if the system time went backwards for any reason,
           RateLimiter will handle it. Otherwise RateLimiter would break by
           not starting a new limiting period for possibly a very long time.
        """
        now_mock.return_value = START_DATETIME
        rl_obj = rate_limiter.RateLimiter(3, 5)
        self.assertEqual(START_DATETIME, rl_obj.current_limit_period_start)
        now_mock.return_value = PAST_DATETIME
        rl_obj.withdraw_items()
        self.assertTrue(new_limit_period_mock.called)
