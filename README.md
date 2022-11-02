# px-log

This is a log-colorizer for [logrus](https://github.com/sirupsen/logrus)-based logs, customized for Portworx logs.

## Usage

```
usage: px-log [options] [<log1> [<log2>...]]

Portworx log parser.

positional arguments:
  logs                  log files to parse

optional arguments:
  -h, --help            show this help message and exit
  -A, --asctime         use ASCII time  (dfl: "%F %T" format)
  -R, --reltime         use relative time
  -F FORMAT, --fmt FORMAT
                        specify format  (dfl: "%(time)19s %(lcode)s %(msg)-100s %(misc)s")
  -V, --version         display version

examples:
    px-log px1.log px2.log          # display given log-files
    cat px2.log | px-log            # parse logs from STDIN
    kubectl -n kube-system logs portworx-XXX | px-log
    px-log --fmt "%(asctime)19s @%(host)s [%(level)s] %(msg)s" px3.log
    px-log --fmt "%(reltime)11s %(file)19s] %(level)8.8s: %(msg)s" px4.log
```

### More tips

Set the `PX_LOG_FORMAT` environment variable to change the default output format:

```bash
export PX_LOG_FORMAT='%(time)19s %(lcode)s %(msg)s'
px-log /tmp/px5.log
```

Configure `less` pager to automatically use `px-log`:

```bash
export LESSOPEN="|/usr/local/bin/px-log %s"
export LESS='-RS'
less /tmp/px6.log
```

## Building

The script can be used "as is", provided you have `python3` installed on your system.

Alternatively, you can compile it into a standalone, executable and use it without `python3`:

    make distclean
    make all
    make install
