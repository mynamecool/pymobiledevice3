import posixpath
import shlex
from dataclasses import asdict

import click
from humanfriendly.tables import format_smart_table

from pymobiledevice3.cli.cli_common import print_object, Command
from pymobiledevice3.exceptions import DvtDirListError
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService, ConnectionDetectionEvent


@click.group()
def cli():
    """ developer cli """
    pass


@cli.group()
def developer():
    """ developer options """
    pass


@developer.command('proclist', cls=Command)
@click.option('--nocolor', is_flag=True)
def proclist(lockdown, nocolor):
    """ show process list """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        processes = dvt.proclist()
        for process in processes:
            if 'startDate' in process:
                process['startDate'] = str(process['startDate'])

        print_object(processes, colored=not nocolor)


@developer.command('applist', cls=Command)
@click.option('--nocolor', is_flag=True)
def applist(lockdown, nocolor):
    """ show application list """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        apps = dvt.applist()
        print_object(apps, colored=not nocolor)


@developer.command('kill', cls=Command)
@click.argument('pid', type=click.INT)
def kill(lockdown, pid):
    """ Kill a process by its pid. """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        dvt.kill(pid)


@developer.command('launch', cls=Command)
@click.argument('arguments', type=click.STRING)
@click.option('--kill-existing/--no-kill-existing', default=True)
@click.option('--suspended', is_flag=True)
def launch(lockdown, arguments: str, kill_existing: bool, suspended: bool):
    """
    Launch a process.
    :param arguments: Arguments of process to launch, the first argument is the bundle id.
    :param kill_existing: Whether to kill an existing instance of this process.
    :param suspended: Same as WaitForDebugger.
    """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        parsed_arguments = shlex.split(arguments)
        pid = dvt.launch(parsed_arguments[0], parsed_arguments[1:], kill_existing, suspended)
        print(f'Process launched with pid {pid}')


@developer.command('shell', cls=Command)
def shell(lockdown):
    """ Launch developer shell. """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        dvt.shell()


def show_dirlist(dvt, dirname, recursive=False):
    try:
        filenames = dvt.ls(dirname)
    except DvtDirListError:
        return

    for filename in filenames:
        filename = posixpath.join(dirname, filename)
        print(filename)
        if recursive:
            show_dirlist(dvt, filename, recursive=recursive)


@developer.command('ls', cls=Command)
@click.argument('path', type=click.Path(exists=False))
@click.option('-r', '--recursive', is_flag=True)
def ls(lockdown, path, recursive):
    """ List directory. """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        show_dirlist(dvt, path, recursive=recursive)


@developer.command('device-information', cls=Command)
@click.option('--nocolor', is_flag=True)
def device_information(lockdown, nocolor):
    """ Print system information. """
    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        print_object({
            'system': dvt.system_information(),
            'hardware': dvt.hardware_information(),
            'network': dvt.network_information(),
        }, colored=not nocolor)


@developer.command('netstat', cls=Command)
def netstat(lockdown):
    """ Print information about current network activity. """

    columns = ['SRC', 'DST']
    rows = []

    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        for event in dvt.network_monitor():
            if isinstance(event, ConnectionDetectionEvent):
                rows.append([f'{event.local_address.data.address}:{event.local_address.port}',
                             f'{event.remote_address.data.address}:{event.remote_address.port}'])
            else:
                break
    print(format_smart_table(rows, columns))


@developer.group('sysmon')
def sysmon():
    """ System monitor options. """


@sysmon.command('processes', cls=Command)
@click.option('-f', '--fields', help='field names splitted by ",".')
def sysmon_processes(lockdown, fields):
    """ show currently running processes information. """

    if fields is not None:
        fields = fields.split(',')

    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        with dvt.sysmontap() as sysmon:
            for row in sysmon:
                if 'Processes' in row:
                    processes = row['Processes'].items()
                    break

    for pid, process in processes:
        attrs = dvt.SysmonProcAttributes(*process)

        print(f'{attrs.name} ({attrs.pid})')
        attrs_dict = asdict(attrs)

        for name, value in attrs_dict.items():
            if (fields is None) or (name in fields):
                print(f'\t{name}: {value}')


@sysmon.command('system', cls=Command)
@click.option('-f', '--fields', help='field names splitted by ",".')
def sysmon_system(lockdown, fields):
    """ show current system stats. """

    if fields is not None:
        fields = fields.split(',')

    with DvtSecureSocketProxyService(lockdown=lockdown) as dvt:
        with dvt.sysmontap() as sysmon:
            for row in sysmon:
                if 'System' in row:
                    system = dvt.SysmonSystemAttributes(*row['System'])
                    break

    attrs_dict = asdict(system)
    for name, value in attrs_dict.items():
        if (fields is None) or (name in fields):
            print(f'{name}: {value}')
