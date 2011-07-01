#!/usr/bin/python
"""
Fuse interface to Rackspace Cloudfiles & Openstack Object Storage

FIXME sometimes gives this error

LOOKUP /test
getattr /test
DEBUG:root:getattr('/test',) {}: enter
DEBUG:root:stat '/test'
DEBUG:root:stat path '/test'
DEBUG:root:listdir ''
DEBUG:root:listdir root
WARNING:root:stat: Response error: 400: Bad request syntax ('0')
DEBUG:root:getattr: caught error: [Errno 1] Operation not permitted: 400: Bad request syntax ('0')
DEBUG:root:getattr: returns -1
   unique: 111, error: -1 (Operation not permitted), outsize: 16

FIXME retry?
"""

# FIXME how do logging?

# FIXME make it single threaded

import fuse
from time import time
import stat
import os
import errno
import logging
from ftpcloudfs.fs import CloudFilesFS
from functools import wraps

fuse.fuse_python_api = (0, 2)
fuse.feature_assert('stateful_files', 'has_init')

def return_errnos(func):
    """
    Decorator to catch EnvironmentError~s and return negative errnos from them

    Other exceptions are not caught.
    """
    @wraps(func)
    def wrapper(*args,**kwargs):
        name = getattr(func, "func_name", "unknown")
        try:
            logging.debug("%s%r %r: enter" % (name, args[1:], kwargs))
            rc = func(*args,**kwargs)
        except EnvironmentError, e:
            logging.debug("%s: caught error: %s" % (name, e))
            rc = -e.errno
        logging.debug("%s: returns %r" % (name, rc))
        return rc
    return wrapper

def flag2mode(flags):
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)

    return m

class CloudFuseFile(object):
    """
    An open file
    """

    def __init__(self, path, flags, *mode):
        #self.parent = parent
        #self.fs = fs
        self.path = path
        self.reading = self.writing = False
        if flags & (os.O_WRONLY|os.O_CREAT):
            mode = "w"
            self.writing = True
        elif flags & os.O_RDWR:
            # Not supported!
            mode = "rw"
            self.reading = True
            self.writing = True
        else:
            mode = "r"
            self.reading = True
        if flags & os.O_APPEND:
            mode += "+"
        # FIXME ignores os.O_TRUNC, os.O_EXCL
        self.file = self.fs.open(path, mode)
        if self.writing:
            self.parent.file_opened(self.path)

    @return_errnos
    def read(self, length, offset):
        # FIXME self.file.seek(offset)
        # check we aren't really seeking
        return self.file.read(length)

    @return_errnos
    def write(self, buf, offset):
        # FIXME self.file.seek(offset)
        # check we aren't really seeking
        self.file.write(buf)
        return len(buf)

    @return_errnos
    def release(self, flags):
        self.file.close()
        if self.writing:
            self.parent.file_closed(self.path)

    @return_errnos
    def fsync(self, isfsyncfile):
        pass

    @return_errnos
    def flush(self):
        pass

    @return_errnos
    def fgetattr(self):
        if self.writing:
            logging.debug("Returning synthetic stat for open file %r" % self.path)
            mode = 0644|stat.S_IFREG
            mtime = time()
            bytes = 0           # FIXME could read bytes so far out of the open file
            count = 1
            return os.stat_result((mode, 0L, 0L, count, 0, 0, bytes, mtime, mtime, mtime))
        return self.fs.stat(self.path)

    @return_errnos
    def ftruncate(self, len):
        # FIXME could implement this
        # maybe should ignore if write pos = 0
        return -errno.ENOSYS

    @return_errnos
    def lock(self, cmd, owner, **kw):
        return -errno.ENOSYS

class CloudFuse(fuse.Fuse):
    """
    Fuse interface to Rackspace Cloudfiles & Openstack Object Storage
    """
    CONFIG_KEYS = ('username','api_key','cache_timeout','authurl','use_snet')
    INT_CONFIG_KEYS = ('cache_timeout',)
    BOOL_CONFIG_KEYS = ('use_snet',)

    def __init__(self, username=None, api_key=None, cache_timeout=600, authurl=None, use_snet=False, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        self.username = username
        self.api_key = api_key
        self.cache_timeout = cache_timeout
        self.authurl = authurl
        self.use_snet = use_snet
        self.read_config()
        self.fs = CloudFilesFS(self.username, self.api_key, servicenet=self.use_snet, authurl=self.authurl)
        self.open_files = {}    # count of open files
        self.file_class.fs = self.fs # FIXME untidy and not re-entrant!
        self.file_class.parent = self # FIXME
        logging.debug("Finished init")

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.username)

    def file_opened(self, path):
        """Keep track of a file being opened"""
        logging.debug("File opened: %r" % path)
        self.open_files[path] = self.open_files.get(path, 0) + 1
        logging.debug("open files: %r" % self.open_files)

    def file_closed(self, path):
        """Keep track of a file being closed"""
        logging.debug("File closed: %r" % path)
        count = self.open_files.get(path)
        if count is None:
            return
        count -= 1
        if count:
            self.open_files[path] = count
        else:
            del self.open_files[path]
        logging.debug("open files: %r" % self.open_files)

    def read_config(self, config="~/.cloudfuse"):
        """
        Reads the config file in ~/.cloudfuse
        """
        config = os.path.expanduser(config)
        try:
            fd = open(config, "r")
        except IOError:
            logging.warning("Failed to read config file %r" % config)
            return
        try:
            for line in fd:
                try:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key not in self.CONFIG_KEYS:
                        logging.warning("Ignoring unknown config key %r" % key)
                        continue
                    if key in self.INT_CONFIG_KEYS:
                        key = int(key)
                    if key in self.BOOL_CONFIG_KEYS:
                        key = value == "true"
                    logging.debug("setting %r = %r from %r" % (key, value, config))
                    setattr(self, key, value)
                except ValueError:
                    logging.warning("Ignoring bad line in %r: %r" % (config, line))
                    continue
        finally:
            fd.close()

    @return_errnos
    def getattr(self, path):
        """Stat the path"""
        # FIXME should be write files..
        # If have a file open for write it may not actually exist yet
        if path in self.open_files:
            logging.debug("Returning synthetic stat for open file %r" % path)
            mode = 0644|stat.S_IFREG
            mtime = time()
            bytes = 0           # FIXME could read bytes so far out of the open file
            count = 1
            return os.stat_result((mode, 0L, 0L, count, 0, 0, bytes, mtime, mtime, mtime))
        return self.fs.stat(path)

    @return_errnos
    def readdir(self, path, offset):
        # FIXME use yield?
        # What about other attributes?
        # What about . and .. ?
        return [ fuse.Direntry(leaf) for leaf in self.fs.listdir(path) ]

    @return_errnos
    def mythread(self):
        return -errno.ENOSYS

    @return_errnos
    def chmod(self, path, mode):
        return 0                # FIXME not really!
        return -errno.ENOSYS

    @return_errnos
    def chown(self, path, uid, gid):
        return 0                # FIXME not really!
        return -errno.ENOSYS

    @return_errnos
    def link(self, dst, src):
        return -errno.ENOSYS

    @return_errnos
    def mkdir(self, path, mode):
        self.fs.mkdir(path)
        return 0

    @return_errnos
    def mknod(self, path, mode, dev):
        # FIXME could do with a better touch method...
        if not stat.S_ISREG(mode):
            return -errno.ENOSYS
        fd = self.fs.open(path, "w")
        fd.close()

    @return_errnos
    def readlink(self, path):
        return -errno.ENOSYS

    @return_errnos
    def rename(self, src, dst):
        self.fs.rename(src, dst)
        return 0

    @return_errnos
    def rmdir(self, path):
        self.fs.rmdir(path)
        return 0

    @return_errnos
    def statfs(self):
        """
        Information about the whole filesystem which we collect from the container stats
        """
        bytes = 0
        files = 0
        for leaf, stat in self.fs.listdir_with_stat("/"):
            bytes += stat.st_size
            files += stat.st_nlink
        block_size = 4096
        used = bytes // block_size
        total = 1024*1024*1024*1024 // block_size
        while used >= total:
            total *= 2
        free = total - used
        total_files = 1024*1024
        while files >= total_files:
            total_files *= 2
        free_files = total_files - files
        return fuse.StatVfs(
            f_bsize = block_size,  # preferred size of file blocks, in bytes
            f_frsize = block_size,# fundamental size of file blcoks, in bytes
            f_blocks = total, # total number of blocks in the filesystem
            f_bfree = free, # number of free blocks
            f_bavail = free,    # Free blocks available to non-super user.
            f_files = total_files, # total number of file inodes
            f_ffree = free_files, # nunber of free file inodes
            )

    @return_errnos
    def symlink(self, dst, src):
        return -errno.ENOSYS

    @return_errnos
    def truncate(self, path, size):
        # FIXME if is open for write, do nothing
        fd = self.fs.open(path, "w")
        # FIXME nasty!
        fd.write("\000" * size)
        fd.close()
        return 0
        #return -errno.ENOSYS

    @return_errnos
    def unlink(self, path):
        self.fs.remove(path)
        return 0

    @return_errnos
    def utime(self, path, times):
        return 0                # FIXME not really!
        return -errno.ENOSYS

    #@return_errnos
    #def file_class(self, path, flags, *mode):
    #    """
    #    Returns a class which acts like a python file object
    #    """
    #    return CloudFuseFile(self, self.fs, path, flags, *mode)
    file_class = CloudFuseFile


def main():
    fs = CloudFuse(version="%prog " + fuse.__version__,
                       usage=CloudFuse.__doc__.strip(),
                       dash_s_do='setsingle')

    fs.parser.add_option(mountopt="root", metavar="PATH", default='/',
                         help="mirror filesystem from under PATH [default: %default]")
    fs.parse(values=fs, errex=1)

    # FIXME Is there a better way than this?
    debug = "debug" in fs.fuse_args.optlist
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    #fs.flags = 0
    #fs.multithreaded = 0
    #fs.main()

    fs.main()

if __name__ == '__main__':
    main()
