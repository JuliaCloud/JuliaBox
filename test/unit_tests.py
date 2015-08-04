import datetime
import os
import docker

from jbox_util import JBoxCfg, LoggerMixin, unique_sessname
from juliabox import db
from juliabox.db import JBoxDynConfig, JBoxSessionProps, JBoxUserV2
from juliabox.cloud import JBoxCloudPlugin
from juliabox.cloud import Compute

conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../conf'))
conf_file = os.path.join(conf_dir, 'tornado.conf')
user_conf_file = os.path.join(conf_dir, 'jbox.user')

JBoxCfg.read(conf_file, user_conf_file)
JBoxCfg.dckr = docker.Client()

LoggerMixin.configure()
db.configure()
Compute.configure()

TESTCLSTR = 'testcluster'


class TestDBTables(LoggerMixin):
    @staticmethod
    def test():
        sprops = JBoxSessionProps(unique_sessname('tanmaykm@gmail.com'))
        TestDBTables.log_debug("JBoxSessionProps. user_id: %s, snapshot_id: %s, message: %s",
                               sprops.get_user_id(),
                               sprops.get_snapshot_id(),
                               sprops.get_message())

        JBoxDynConfig.set_cluster_leader(TESTCLSTR, 'testinstance')
        assert JBoxDynConfig.get_cluster_leader(TESTCLSTR) == 'testinstance'
        JBoxDynConfig.unset_cluster_leader(TESTCLSTR)
        assert JBoxDynConfig.get_cluster_leader(TESTCLSTR) is None

        assert JBoxDynConfig.get_allow_registration(TESTCLSTR)
        JBoxDynConfig.set_allow_registration(TESTCLSTR, False)
        assert not JBoxDynConfig.get_allow_registration(TESTCLSTR)
        JBoxDynConfig.set_allow_registration(TESTCLSTR, True)
        assert JBoxDynConfig.get_allow_registration(TESTCLSTR)

        assert JBoxDynConfig.get_registration_hourly_rate(TESTCLSTR) == 60
        JBoxDynConfig.set_registration_hourly_rate(TESTCLSTR, 20)
        assert JBoxDynConfig.get_registration_hourly_rate(TESTCLSTR) == 20
        JBoxDynConfig.set_registration_hourly_rate(TESTCLSTR, 60)
        assert JBoxDynConfig.get_registration_hourly_rate(TESTCLSTR) == 60

        assert JBoxDynConfig.get_message(TESTCLSTR) is None
        JBoxDynConfig.set_message(TESTCLSTR, "hello world", datetime.timedelta(minutes=1))
        assert JBoxDynConfig.get_message(TESTCLSTR) == "hello world"

        JBoxDynConfig.set_user_home_image(TESTCLSTR, "juliabox-user-home-templates", "user_home_28Nov2014.tar.gz")
        assert JBoxDynConfig.get_user_home_image(TESTCLSTR) == ("juliabox-user-home-templates",
                                                                "user_home_28Nov2014.tar.gz")

        num_pending_activations = JBoxUserV2.count_pending_activations()
        TestDBTables.log_debug("pending activations: %d", num_pending_activations)

        count_created = JBoxUserV2.count_created(48)
        TestDBTables.log_debug("accounts created in last 1 hour: %d", count_created)


class TestSES(LoggerMixin):
    @staticmethod
    def test():
        plugin = JBoxCloudPlugin.jbox_get_plugin(JBoxCloudPlugin.PLUGIN_SENDMAIL)
        plugin.send_email('tanmaykm@gmail.com', 'admin@juliabox.org', "test SES",
                          """hello world
                          Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt
                          ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation
                          ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in
                          reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
                          Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit
                          anim id est laborum.""")

if __name__ == "__main__":
    TestDBTables.test()
    TestSES.test()