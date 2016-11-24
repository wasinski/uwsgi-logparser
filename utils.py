class TimeFrame:

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __contains__(self, datetime):
        if self.start and datetime < self.start:
            return False
        if self.end and datetime > self.end:
            return False
        return True


def humanize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0:
        return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def dict_to_str(d):
    return '({})'.format(', '.join(['%s: %s' % (key, value) for (key, value) in sorted(d.items())]))
