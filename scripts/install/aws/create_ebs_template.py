import time
import math
import os
import stat

import boto
import boto.ec2
import boto.utils
import sh


def retry(tries, delay=1, backoff=2):
    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")

    tries = math.floor(tries)
    if tries < 0:
        raise ValueError("tries must be 0 or greater")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay  # make mutable

            rv = f(*args, **kwargs)  # first attempt
            while mtries > 0:
                if rv is True:  # Done on success
                    return True

                mtries -= 1      # consume an attempt
                time.sleep(mdelay)  # wait...
                mdelay *= backoff  # make future wait longer

                rv = f(*args, **kwargs)  # Try again

            return False  # Ran out of tries :-(

        return f_retry  # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator


def _state_check(obj, state):
    obj.update()
    classname = obj.__class__.__name__
    if classname in ('Snapshot', 'Volume'):
        return obj.status == state
    else:
        return obj.state == state


def _device_exists(dev):
    try:
        mode = os.stat(dev).st_mode
    except OSError:
        return False
    return stat.S_ISBLK(mode)


@retry(20, 0.5, backoff=1.5)
def _wait_for_status(resource, state):
    return _state_check(resource, state)


@retry(20, 0.5, backoff=1.5)
def _wait_for_device(dev):
    return _device_exists(dev)


def _err_exit(msg):
    print("error " + msg)
    exit(-1)


def _status_err_exit(resource, state, msg):
    if not _wait_for_status(resource, state):
        _err_exit(msg)


def _sh_err_exit(fn, msg):
    print(msg + ' ...')
    result = fn()
    if result.exit_code != 0:
        _err_exit(msg)

if __name__ == "__main__":
    REGION = 'us-east-1'
    ZONE = 'us-east-1a'
    DEVICE = '/dev/xvdcz'
    MOUNT = '/tmp/xvdcz'
    DISK_SZ = 10

    instance_id = boto.utils.get_instance_metadata()['instance-id']
    print("running on instance " + instance_id)

    ec2 = boto.ec2.connect_to_region(REGION)
    print("creating volume...")
    vol = ec2.create_volume(DISK_SZ, ZONE, volume_type='gp2')
    _status_err_exit(vol, 'available', 'creating volume')
    print("created volume " + vol.id)

    print("adding tags...")
    ec2.create_tags([vol.id], {"Name": 'jbox_user_disk_template'})

    print("attaching at " + DEVICE + " ...")
    ec2.attach_volume(vol.id, instance_id, DEVICE)
    if (not _wait_for_status(vol, 'in-use')) or (not _wait_for_device(DEVICE)):
        _err_exit("attaching at " + DEVICE)

    _sh_err_exit(lambda: sh.sudo.mkfs(DEVICE, t="ext4"), 'making ext4 file system')

    if not os.path.exists(MOUNT):
        os.makedirs(MOUNT)
    _sh_err_exit(lambda: sh.sudo.mount(DEVICE, MOUNT), 'mounting device at ' + MOUNT)
    _sh_err_exit(lambda: sh.sudo.chown('-R', str(os.getuid())+':'+str(os.getgid()), MOUNT), 'changing file owmership')
    _sh_err_exit(lambda: sh.sudo.umount(MOUNT), 'ummounting device from ' + MOUNT)
    os.rmdir(MOUNT)

    print('creating snapshot...')
    snap = vol.create_snapshot('JuliaBox User Disk Snapshot')
    _status_err_exit(snap, 'completed', 'creating snapshot')
    print('created snapshot ' + snap.id)
    print('adding tags...')
    ec2.create_tags([snap.id], {'Name': 'jbox_user_disk_snapshot'})

    print('detaching volume...')
    ec2.detach_volume(vol.id, instance_id=instance_id, device=DEVICE)
    _status_err_exit(vol, 'available', 'detaching volume')

    print ('deleting volume...')
    ec2.delete_volume(vol.id)

    print('done.')
