from collections import OrderedDict
from os import makedirs

from common.sftp.action_codes import SFTPActionCodes


class SFTPAction:
    def __init__(self, mirrorer, action_code, path, **kwargs):
        self.mirrorer = mirrorer
        self.action_code = action_code
        self.path = path
        self.kwargs = kwargs

    def run(self):
        if self.action_code == SFTPActionCodes.LMKDIR:
            makedirs(self.path, mode=self.kwargs['mode'], exist_ok=True)

    def to_json(self):
        return self.to_dict()

    def to_dict(self):
        result_dict = OrderedDict([
            ("action_code", self.action_code),
            ("path", self.path),
        ])
        result_dict.update(self.kwargs)
        return result_dict

    def __repr__(self):
        args = ["{}={}".format(key, value) for key, value in self.to_dict().items()]
        args_string = ",".join(args)
        return "SFTPAction({})".format(args_string)
