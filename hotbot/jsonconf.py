# js.py - Classes to make Python feel a little more like JavaScript
# Author: Adam Haile
# License: MIT

import copy
import json
import os

#Gives Python dict ability to use dot notation for all keys and adds other helpful methods


class jsdict(dict):

    def __init__(self, *a, **k):
        super(jsdict, self).__init__(*a, **k)
        #set the internal property dict to itself
        self.__dict__ = self
        #recurses through list and dict types, converting to jsdict
        for k in self.__dict__:
            if isinstance(self.__dict__[k], dict):
                self.__dict__[k] = jsdict(self.__dict__[k])
            elif isinstance(self.__dict__[k], list):
                for i in range(len(self.__dict__[k])):
                    if isinstance(self.__dict__[k][i], dict):
                        self.__dict__[k][i] = jsdict(self.__dict__[k][i])

    #Undefined keys now return None instead of throwing exception
    def __getattr__(self, name):
        return None

    #Adds missing keys from given dict into this dict.
    #Optionally overwrite keys that do exist
    def upgrade(self, a, overwrite=False):
        a = jsdict(a)
        for k, v in a.items():
            if k not in self or overwrite:
                self[k] = v
        return self

    #deep clone on whole dict
    def clone(self):
        return copy.deepcopy(self)

    #output dict as JSON dump
    def json(self):
        return json.dumps(self)

#same as jsdict but directly represents itself as JSON


class jsondict(jsdict):

    def __init__(self, *a, **k):
        super(jsondict, self).__init__(*a, **k)

    def __repr__(self):
        return self.json()

    def __str__(self):
        return self.json()


class jsonconf(object):

    def __init__(self, file_path, *a, **k):
        self.__dict__['file_path'] = file_path
        self.__dict__['__dict'] = jsdict(*a, **k)
        self.reload()

    def __repr__(self):
        return self.__dict__['__dict'].__repr__()

    def __str__(self):
        return self.__dict__['__dict'].__str__()

    def __getattr__(self, name):
        return self.__getitem__(name)

    def __setattr__(self, name, value):
        return self.__dict__['__dict'].__setattr__(name, value)

    def __delattr__(self, name):
        return self.__dict__['__dict'].__delattr__(name)

    def __getitem__(self, key):
        try:
            return self.__dict__['__dict'].__getitem__(key)
        except KeyError:
            return None

    def __setitem__(self, key, value):
        return self.__dict__['__dict'].__setitem__(key, value)

    def __delitem__(self, key):
        return self.__dict__['__dict'].__delitem__(key)

    def __iter__(self):
        return self.__dict__['__dict'].__iter__()

    def update(self, *a, **k):
        self.__dict__['__dict'] = jsdict(*a, **k)

    def reload(self):
        data = None
        # print self.__dict__['file_path']
        if not os.path.exists(self.__dict__['file_path']):
            open(self.__dict__['file_path'], "w+").close()
        with open(self.__dict__['file_path'], mode="r") as fp:
            try:
                data = json.load(fp)
            except ValueError:  # empty file
                data = {}
        if data:
            self.__dict__['__dict'] = jsdict(data)

    def save(self):
        with open(self.__dict__['file_path'], mode="w") as fp:
            json.dump(self.__dict__['__dict'], fp, indent=4, sort_keys=True)
