# Copyright (c) 2013 Rackspace
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

import os

from trove.common import cfg
from trove.common import utils as utils
from trove.common import exception
from trove.common import instance as rd_instance
from trove.guestagent import pkg
from trove.guestagent.datastore import service
from trove.guestagent.datastore.redis import system
from trove.openstack.common import log as logging
from trove.openstack.common.gettextutils import _

LOG = logging.getLogger(__name__)
TMP_REDIS_CONF = '/tmp/redis.conf.tmp'
TIME_OUT = 1200
CONF = cfg.CONF
packager = pkg.Package()


def _load_redis_options():
    """
    Reads the redis config file for all redis options.
    Right now this does not do any smart parsing and returns only key
    value pairs as a str, str.
    So: 'foo bar baz' becomes {'foo' : 'bar baz'}
    """
    options = {}
    with open(system.REDIS_CONFIG, 'r') as fd:
        for opt in fd.readlines():
            opt = opt.rstrip().split(' ')
            options.update({opt[0]: ' '.join(opt[1:])})
    return options


class RedisAppStatus(service.BaseDbStatus):
    """
    Handles all of the status updating for the redis guest agent.
    """
    @classmethod
    def get(cls):
        """
        Gets an instance of the RedisAppStatus class.
        """
        if not cls._instance:
            cls._instance = RedisAppStatus()
        return cls._instance

    def _get_actual_db_status(self):
        """
        Gets the actual status of the Redis instance
        First it attempts to make a connection to the redis instance
        by making a PING request.
        If PING does not return PONG we do a ps
        to see if the process is blocked or hung.
        This implementation stinks but redis-cli only returns 0
        at this time.
        http://redis.googlecode.com/svn/trunk/redis-cli.c
        If we raise another exception.ProcessExecutionError while
        running ps.
        We attempt to locate the PID file and see if the process
        is crashed or shutdown.
        Remeber by default execute_with_timeout raises this exception
        if a non 0 status code is returned from the cmd called.
        """
        options = _load_redis_options()
        out = ""
        err = ""
        try:
            if 'requirepass' in options:
                LOG.info(_('Password is set running ping with password'))
                out, err = utils.execute_with_timeout(
                    system.REDIS_CLI,
                    '-a',
                    options['requirepass'],
                    'PING',
                    run_as_root=True,
                    root_helper='sudo')
            else:
                LOG.info(_('Password not set running ping without password'))
                out, err = utils.execute_with_timeout(
                    system.REDIS_CLI,
                    'PING',
                    run_as_root=True,
                    root_helper='sudo')
            LOG.info(_('Redis is RUNNING.'))
            return rd_instance.ServiceStatuses.RUNNING
        except exception.ProcessExecutionError:
            LOG.error(_('Process execution error on redis-cli'))
        if 'PONG' not in out:
            try:
                out, err = utils.execute_with_timeout('/bin/ps', '-C',
                                                      'redis-server', 'h')
                pid = out.split()[0]
                msg = _('Redis pid: %s') % (pid)
                LOG.info(msg)
                LOG.info(_('Service Status is BLOCKED.'))
                return rd_instance.ServiceStatuses.BLOCKED
            except exception.ProcessExecutionError:
                pid_file = options.get('pidfile',
                                       '/var/run/redis/redis-server.pid')
                if os.path.exists(pid_file):
                    LOG.info(_('Service Status is CRASHED.'))
                    return rd_instance.ServiceStatuses.CRASHED
                else:
                    LOG.info(_('Service Status is SHUTDOWN.'))
                    return rd_instance.ServiceStatuses.SHUTDOWN


class RedisApp(object):
    """
    Handles installation and configuration of redis
    on a trove instance.
    """

    def __init__(self, status, state_change_wait_time=None):
        """
        Sets default status and state_change_wait_time
        """
        if state_change_wait_time:
            self.state_change_wait_time = state_change_wait_time
        else:
            self.state_change_wait_time = CONF.state_change_wait_time
        self.status = status

    def install_if_needed(self, packages):
        """
        Install redis if needed do nothing if it is already installed.
        """
        LOG.info(_('Preparing Guest as Redis Server'))
        if not packager.pkg_is_installed(packages):
            LOG.info(_('Installing Redis'))
            self._install_redis(packages)
        LOG.info(_('Dbaas install_if_needed complete'))

    def complete_install_or_restart(self):
        """
        finalize status updates for install or restart.
        """
        self.status.end_install_or_restart()

    def _install_redis(self, packages):
        """
        Install the redis server.
        """
        LOG.debug(_('Installing redis server'))
        msg = _("Creating %s") % (system.REDIS_CONF_DIR)
        LOG.debug(msg)
        utils.execute_with_timeout('mkdir',
                                   '-p',
                                   system.REDIS_CONF_DIR,
                                   run_as_root=True,
                                   root_helper='sudo')
        pkg_opts = {}
        packager.pkg_install(packages, pkg_opts, TIME_OUT)
        self.start_redis()
        LOG.debug(_('Finished installing redis server'))

    def _enable_redis_on_boot(self):
        """
        Enables redis on boot.
        """
        LOG.info(_('Enabling redis on boot.'))
        if os.path.isfile(system.REDIS_INIT):
            LOG.info(_("OS Using Upstart"))
            cmd = "sudo sed -i '/^manual$/d' %s" % (system.REDIS_INIT)
            utils.execute_with_timeout(cmd,
                                       shell=True)
        else:
            cmd = 'sudo %s' % (system.REDIS_CMD_ENABLE)
            utils.execute_with_timeout(cmd,
                                       shell=True)

    def _disable_redis_on_boot(self):
        """
        Disables redis on boot.
        """
        LOG.info(_('Disabling redis on boot.'))
        if os.path.isfile(system.REDIS_INIT):
            LOG.info(_("OS Using Upstart"))
            utils.execute_with_timeout('echo',
                                       "'manual'",
                                       '>>',
                                       system.REDIS_INIT,
                                       run_as_root=True,
                                       root_helper='sudo')
        else:
            cmd = 'sudo %s' % (system.REDIS_CMD_DISABLE)
            utils.execute_with_timeout(cmd,
                                       shell=True)

    def stop_db(self, update_db=False, do_not_start_on_reboot=False):
        """
        Stops the redis application on the trove instance.
        """
        LOG.info(_('Stopping redis...'))
        if do_not_start_on_reboot:
            self._disable_redis_on_boot()
        cmd = 'sudo %s' % (system.REDIS_CMD_STOP)
        utils.execute_with_timeout(cmd,
                                   shell=True)
        if not self.status.wait_for_real_status_to_change_to(
                rd_instance.ServiceStatuses.SHUTDOWN,
                self.state_change_wait_time, update_db):
            LOG.error(_('Could not stop Redis!'))
            self.status.end_install_or_restart()

    def restart(self):
        """
        Restarts the redis daemon.
        """
        try:
            self.status.begin_restart()
            self.stop_db()
            self.start_redis()
        finally:
            self.status.end_install_or_restart()

    def write_config(self, config_contents):
        """
        Write the redis config.
        """
        with open(TMP_REDIS_CONF, 'w') as fd:
            fd.write(config_contents)
        utils.execute_with_timeout('mv',
                                   TMP_REDIS_CONF,
                                   system.REDIS_CONFIG,
                                   run_as_root=True,
                                   root_helper='sudo')

    def start_redis(self, update_db=False):
        """
        Start the redis daemon.
        """
        LOG.info(_("Starting redis..."))
        self._enable_redis_on_boot()
        try:
            cmd = 'sudo %s' % (system.REDIS_CMD_START)
            utils.execute_with_timeout(cmd,
                                       shell=True)
        except exception.ProcessExecutionError:
            pass
        if not self.status.wait_for_real_status_to_change_to(
                rd_instance.ServiceStatuses.RUNNING,
                self.state_change_wait_time, update_db):
            LOG.error(_("Start up of redis failed!"))
            try:
                utils.execute_with_timeout('pkill', '-9',
                                           'redis-server',
                                           run_as_root=True,
                                           root_helper='sudo')
            except exception.ProcessExecutionError as p:
                LOG.error('Error killing stalled redis start command.')
                LOG.error(p)
            self.status.end_install_or_restart()
