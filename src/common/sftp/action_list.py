from collections import OrderedDict
from operator import itemgetter

from common.sftp.action import SFTPAction
from common.sftp.action_codes import SFTPActionCodes


class SFTPActionList:
    def __init__(self, mirrorer):
        self.mirrorer = mirrorer
        self.dir_actions = OrderedDict()
        self.file_actions = OrderedDict()

    def add(self, action):
        if action.action_code in SFTPActionCodes.DIR_ACTION_CODES:
            self.dir_actions[action.path] = action
        elif action.action_code in SFTPActionCodes.FILE_ACTION_CODES:
            self.file_actions[action.path] = action

    def create(self, action_code, path, **kwargs):
        action = SFTPAction(self.mirrorer, action_code, path, **kwargs)
        self.add(action)

    def do_actions(self, dry_run=False):
        for path, action in self.items():
            if dry_run:
                print("Would have run: {path} -> {action_code}".format(path=action.path, action_code=action.action_code))
            else:
                print("Running: {path} -> {action_code}".format(path=action.path, action_code=action.action_code))
                action.run()

    def items(self):
        sorted_dir_actions = sorted(self.dir_actions.items(), key=itemgetter(0))
        sorted_file_actions = sorted(self.file_actions.items(), key=itemgetter(0))
        return sorted_dir_actions + sorted_file_actions

    def clear(self):
        self.dir_actions = OrderedDict()
        self.file_actions = OrderedDict()

    def to_json(self):
        return OrderedDict(self.items())

    def __repr__(self):
        return str(self.to_json())
