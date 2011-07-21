pycloudfuse
===========

This is a FUSE (File-system in Userspace) interface to Rackspace Cloudfiles & Openstack Object Storage

Copyright (C) 2011 by Memset Ltd. http://www.memset.com/

It was born out of the difficulty of experimenting with the original C version https://github.com/redbo/cloudfuse .

It is currently in a just working state!


Install
-------

Requirements:

- python (2.6)
- python-fuse (0.2.1)
- python-rackspace-cloudfiles (1.7.9)
- python-ftp-cloudfs (0.9)

These are the minimum recommended versions based in our testing
environment.

To install the software, run following command:

    python setup.py install


Usage
-----

Put your credentials to the Object Storage in a file called .cloudfuse in your home directory (this is compatible with the C cloudfuse)

    username=USERNAME
    api_key=PASSWORD
    authurl=https://auth.PROVIDER.com/v1.0

Once you have done that you can use

    pycloudfuse /path/to/mount

To mount that storage.  To unmount use

   fusermount -u /path/to/mount

Most operations are supported.  Note that "df -i" shows the inodes which is the number of files used.

Run

    pycloudfuse -h

To see a list of options, mostly inherited directly from fuse

To debug (or hack on) run like this

   pycloudfuse -d -f ~/mnt/cloudfuse/

Which will print an enormous amount of debugging information to the console.  You'll need to fusermount -u it from another terminal as you can't interrupt it with CTRL-C.


Things to note
--------------

You can only make directories in the root.  Each root is a container object in the object storage.

Rename does work!

It won't work for more than 10,000 objects in a directory.


Todo
----

Make some mount options for user/key/authurl etc

Fix some of the FIXMEs


License
-------

This is free software under the terms of MIT license (check COPYING file
included in this package).

The server is loosely based on the BSD licensed sftpd server code from:

    http://code.google.com/p/pyfilesystem/


Contact and support
-------------------

The project website is at:

  https://github.com/memset/pycloudfuse

There you can file bug reports, ask for help or contribute patches.


Authors
-------

- Nick Craig-Wood <nick@memset.com>
