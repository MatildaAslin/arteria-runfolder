import unittest
import time
from arteria.testhelpers import TestFunctionDelta, BaseRestTest
import os


def line_count(path):
    count = 0
    for _ in open(path).xreadlines():
        count += 1
    return count


class RestApiTestCase(BaseRestTest):
    def _base_url(self):
        env_key = "ARTERIA_RUNFOLDER_SVC_URL"
        if env_key in os.environ:
            return os.environ[env_key]
        else:
            return "http://localhost:10800/api/1.0"

    # NOTE: Also tests log files, so currently needs to run from the server
    # itself, and the log files being tested against are assumed to be small
    # These tests are intended to be full integration tests, mocking nothing
    def setUp(self):
        self.messages_logged = TestFunctionDelta(
            lambda: line_count('./runfolder.log'), self, 0.1)

    def test_can_change_log_level(self):
        self.put("./admin/log_level", {"log_level": "DEBUG"})
        resp = self.get("./admin/log_level")
        self.assertEqual(resp.body_obj["log_level"], "DEBUG")

        # For the rest of the test, and by default, we should have log level WARNING
        self.put("./admin/log_level", {"log_level": "WARNING"})

    def test_not_monitored_path_returns_400(self):
        self.get("./runfolders/path/notmonitored/dir/", expect=400)
        # Tornado currently writes two entries for 400, for tornado.general and tornado.access
        self.messages_logged.assert_changed_by_total(2)

    def test_can_create_and_update_state(self):
        # First, we want to make sure it's not there now, resulting in 404 warn log:
        file_postfix = int(1000 * time.time())
        # Ensure that we can create a random runfolder at one of the mountpoints
        path = "{0}/runfolder_inttest_{1}".format(self._get_monitored_dir(), file_postfix)

        self.get("./runfolders/path{0}".format(path), expect=404)

        # Now, create the folder
        self.put("./runfolders/path{0}".format(path), expect=201)
        # Create the complete marker
        self.put("./runfolders/test/markasready/path{0}".format(path))

        # The runfolder should show up in /runfolders
        resp = self.get("./runfolders")
        runfolders = resp.body_obj["runfolders"]
        matching = [runfolder for runfolder in runfolders if runfolder["path"] == path]
        self.assertEqual(len(matching), 1)

        # TODO: Change state to "processing" and ensure it doesn't show up in /runfolders
        self.messages_logged.assert_changed_by_total(2)

    def _get_monitored_dir(self):
        path_to_test_dir = os.path.dirname(os.path.realpath(__file__))
        return "{0}/monitored".format(path_to_test_dir)


if __name__ == '__main__':
    unittest.main()
