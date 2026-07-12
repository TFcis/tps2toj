import os
import logging

def makedirs(*path):
    path = os.path.join(*path)
    logging.debug("Checking exists {}".format(path))
    if not os.path.exists(path):
        logging.debug('Creating {}'.format(path))
        os.makedirs(path)

def symlinkfile(source, target):
    source = os.path.join(*source)
    target = os.path.join(*target)
    if not os.path.lexists(target):
        logging.debug('Linking {} to {}'.format(source, target))
        os.symlink(os.path.abspath(source), target)

def symlinkfolder(source, target):
    source = os.path.join(*source)
    target = os.path.join(*target)
    if not os.path.lexists(target):
        logging.debug('Linking {} to {}'.format(source, target))
        os.symlink(os.path.abspath(source), target, target_is_directory=True)
