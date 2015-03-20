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

import importlib

from arsenal.common import exception


class ImportModuleException(exception.ArsenalException):
    msg_fmt = ("Couldn't import module '%(module_name)s', with package "
               "'%(package)s'")


class FindObjectException(exception.ArsenalException):
    msg_fmt = ("Couldn't find the specified object'%(class_name)s' in "
               "'%(module_name)s'")


class ImproperModuleClassStringFormat(exception.ArsenalException):
    msg_fmt = ("The supplied module.class string was of improper format. Got: "
               "'%(mc_string)s'")


class LoadClass(object):
    """LoadClass provides a way to easily load a specified module/class pair

    If everything goes smoothly, then the specified class will be available
    for instaniation at self.loaded_class. __init__ should raise an exception
    if something goes wrong.

    :param module_class_string: A string specifying the module to load, in the
        following format: 'module_name.ClassName'.
    :param package_prefix: A string specifying the package prefix to apply
        to the module name.

    Example:
        try:
            loader = LoadClass('strategy.ImageInput', package_prefix='arsenal')
        except (ImportModuleException,
                FindObjectException,
                ImproperModuleClassStringFormat) as e:
            print "Something went wrong!"
            raise e
        image_input = loader.loaded_class(<args here>)
        # Do stuff with image_input
    """
    def __init__(self, module_class_string, package_prefix=None):
        self.module = None
        self.loaded_class = None
        self.package_prefix = package_prefix
        self.module_name, self.class_name = (
            self._parse_module_class_string('.' + module_class_string))
        self._import_module()
        self._get_class()

    def instaniate(self, *args, **kwargs):
        return self.loaded_class(*args, **kwargs)

    def _parse_module_class_string(self, module_class_string):
        try:
            dot_index = module_class_string.rfind('.')
        except ValueError:
            raise ImproperModuleClassStringFormat(
                mc_string=module_class_string)

        module_name = module_class_string[0:dot_index]
        class_name = module_class_string[dot_index + 1:]
        return (module_name, class_name)

    def _import_module(self):
        try:
            self.module = importlib.import_module(self.module_name,
                                                  package=self.package_prefix)
        except ImportError:
            raise ImportModuleException(
                module_name=self.module_name, package=self.package_prefix)

    def _get_class(self):
        try:
            self.loaded_class = getattr(self.module, self.class_name)
        except AttributeError:
            raise FindObjectException(module_name=self.module_name,
                                      class_name=self.class_name)
