from collections import OrderedDict
from operator import itemgetter

from durasftp.common.sftp.action import SFTPAction
from durasftp.common.sftp.action_codes import SFTPActionCodes


class SFTPActionList:
    def __init__(self, mirrorer):
        self.mirrorer = mirrorer
        self.ok_actions = OrderedDict()
        self.dir_actions = OrderedDict()
        self.file_actions = OrderedDict()

    def add(self, action):
        if action.action_code == SFTPActionCodes.OK:
            self.ok_actions[action.remote_path] = action
        elif action.action_code in SFTPActionCodes.DIR_ACTION_CODES:
            self.dir_actions[action.remote_path] = action
        elif action.action_code in SFTPActionCodes.FILE_ACTION_CODES:
            self.file_actions[action.remote_path] = action

    def create(self, action_code, remote_path, **kwargs):
        action = SFTPAction(self.mirrorer, action_code, remote_path, **kwargs)
        self.add(action)

    def do_actions(self, callback=None, dry_run=False):
        for remote_path, action in self.items():
            action.run(callback=callback, dry_run=dry_run)

    def items(self):
        sorted_ok_actions = sorted(self.ok_actions.items(), key=itemgetter(0))
        sorted_dir_actions = sorted(self.dir_actions.items(), key=itemgetter(0))
        sorted_file_actions = sorted(self.file_actions.items(), key=itemgetter(0))
        return sorted_ok_actions + sorted_dir_actions + sorted_file_actions

    def filtered_items(self, codes=None):
        filtered_items = self.items()

        if codes is not None:
            # filtered_items = filter(lambda item: item[1].action_code in codes, filtered_items)
            filtered_items = [
                item for item in filtered_items if item[1].action_code in codes
            ]
        return filtered_items

    def clear(self):
        self.dir_actions = OrderedDict()
        self.file_actions = OrderedDict()

    def to_json(self):
        return OrderedDict(self.items())

    def __repr__(self):
        return str(self.to_json())
