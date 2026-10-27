# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import unittest
SCRIPT=Path(__file__).resolve().parents[1]/'tools/sync_sdk_contracts.py'
spec=importlib.util.spec_from_file_location('sync_sdk_contracts',SCRIPT)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
class SdkSyncTests(unittest.TestCase):
    def test_source_is_scoped_to_canonical_owned_sdk(self):
        self.assertEqual('ZairenkaiPrjctX/Zairenkai-Sdk',module.SDK_REPO)
    def test_refuses_short_or_non_sha_commit(self):
        with self.assertRaises(SystemExit): module.sync('main')
        with self.assertRaises(SystemExit): module.sync('a'*39)
    def test_refuses_path_traversal(self):
        with self.assertRaises(SystemExit): module.git_show(Path('/tmp'), 'a'*40, 'contracts/../../etc/passwd')
        with self.assertRaises(SystemExit): module.git_show(Path('/tmp'), 'a'*40, '/contracts/schema.json')
if __name__=='__main__': unittest.main()
