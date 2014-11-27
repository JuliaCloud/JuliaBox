import db
from db import JBoxDynConfig, JBoxAccountingV2, JBoxSessionProps, JBoxUserV2
from jbox_util import read_config, LoggerMixin, unique_sessname
import docker
import datetime
from cloud.aws import CloudHost

dckr = docker.Client()
cfg = read_config()
cloud_cfg = cfg['cloud_host']

LoggerMixin.setup_logger(level=cfg['root_log_level'])
LoggerMixin.DEFAULT_LEVEL = cfg['jbox_log_level']

db.configure_db(cfg)

CloudHost.configure(has_s3=cloud_cfg['s3'],
                    has_dynamodb=cloud_cfg['dynamodb'],
                    has_cloudwatch=cloud_cfg['cloudwatch'],
                    has_autoscale=cloud_cfg['autoscale'],
                    has_route53=cloud_cfg['route53'],
                    has_ebs=cloud_cfg['ebs'],
                    has_ses=cloud_cfg['ses'],
                    scale_up_at_load=cloud_cfg['scale_up_at_load'],
                    scale_up_policy=cloud_cfg['scale_up_policy'],
                    autoscale_group=cloud_cfg['autoscale_group'],
                    route53_domain=cloud_cfg['route53_domain'],
                    region=cloud_cfg['region'],
                    install_id=cloud_cfg['install_id'])


TESTCLSTR = 'testcluster'


class TestDBTables(LoggerMixin):
    @staticmethod
    def test():
        yday = datetime.datetime.now() - datetime.timedelta(hours=24)
        stats = JBoxAccountingV2.get_stats(dates=(yday,))
        TestDBTables.log_debug("stats for yesterday: %s", repr(stats))
        stats = JBoxAccountingV2.get_stats()
        TestDBTables.log_debug("stats for today: %s", repr(stats))

        sprops = JBoxSessionProps(unique_sessname('tanmaykm@gmail.com'))
        TestDBTables.log_debug("JBoxSessionProps. user_id: %s, snapshot_id: %s, message: %s",
                               sprops.get_user_id(),
                               sprops.get_snapshot_id(),
                               sprops.get_message())

        JBoxDynConfig.set_cluster_leader(TESTCLSTR, 'testinstance')
        assert JBoxDynConfig.get_cluster_leader(TESTCLSTR) == 'testinstance'

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

        num_pending_activations = JBoxUserV2.count_pending_activations()
        TestDBTables.log_debug("pending activations: %d", num_pending_activations)

if __name__ == "__main__":
    TestDBTables.test()
