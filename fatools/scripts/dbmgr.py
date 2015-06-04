
import sys, argparse, yaml, csv, transaction
from fatools.lib.utils import cout, cerr, get_dbhandler, tokenize

def init_argparser():

    p = argparse.ArgumentParser('dbmgr')

    p.add_argument('--sqldb', default=False,
            help = 'Sqlite3 database filename')

    p.add_argument('--fsdb', default=False,
            help = 'directory for filesystem-based database')

    p.add_argument('--initdb', default=False, action='store_true',
            help = 'initialize database')

    p.add_argument('--importpanel', default=False,
            help = 'importing panel from YAML file')

    p.add_argument('--importmarker', default=False,
            help = 'importing marker from YAML file')

    p.add_argument('--update', default=False,
            help = 'updating current data in the database')

    p.add_argument('--commit', default=False, action='store_true',
            help = 'commit to database')

    p.add_argument('--upload', default=False,
            help = 'uploading FSA data')

    p.add_argument('--batch', default=False,
            help = 'batch code')

    p.add_argument('--fsadir', default='.',
            help = 'directory containing FSA files')

    p.add_argument('--initbatch', default=False,
            help = 'create new batch')

    p.add_argument('--initsample', default=False,
            help = 'create new sample from sample file')


    p.add_argument('--clearassay', default=False, action='store_true',
            help = 'clear assay')

    p.add_argument('--species', default='',
            help = 'species of markers')

    p.add_argument('--test', default=False, action='store_true',
            help = 'perform test, print error as warning')

    p.add_argument('--abort', default=False, action='store_true',
            help = 'abort for any warning')

    return p



def main(args):

    if not args.test and (args.commit or args.initdb):
        with transaction.manager:
            do_dbmgr(args)
            cerr('** COMMIT to database **')

    else:
        cerr('WARNING -- running without commiting to database!')
        if not args.test:
            keys = input('Do you want to continue [y/n]? ')
            if not keys.lower().strip().startswith('y'):
                sys.exit(1)
            
        do_dbmgr(args)


def do_dbmgr(args, dbh = None, warning=True):

    if not dbh:
        dbh = get_dbhandler(args, initial = args.initdb)

    if args.upload is not False:
        do_upload(args, dbh)
    elif args.initbatch is not False:
        do_initbatch(args, dbh)
    elif args.initsample is not False:
        do_initsample(args, dbh)
    elif args.importpanel is not False:
        do_importpanel(args, dbh)
    elif args.importmarker is not False:
        do_importmarker(args, dbh)
    elif args.initdb is not False:
        do_initdb(args, dbh)
    elif args.clearassay is not False:
        do_clearassay(args, dbh)
    else:
        if warning:
            cerr('Unknown command, nothing to do!')
        return False

    return True


def do_initdb(args, dbh):

    dbh.initdb()



def do_importpanel(args, dbh):

    panels = yaml.load( open(args.importpanel) )

    for code, panel in panels.items():
        if panel['code'] != code:
            cerr('ERR: code for panel %s is not consistent!' % code)
            sys.exit(1)
        p = dbh.Panel()
        p.update( panel )
        if args.update:
            db_p = p.sync(dbh.session)
            cout("INFO: panel %s sync'd." % db_p.code)
        else:
            dbh.session.add(p)
            cout("INFO: panel %s added." % p.code)



def do_importmarker(args, dbh):

    markers = yaml.load(open(args.importmarker))
    # markers is a dict of dict, so need a new instance for updating

    for code, marker in markers.items():
        if marker['code'] != code:
            cerr('ERR: code for marker %s is not consistent!' % code)
            sys.exit(1)
        m = dbh.Marker()
        m.update(marker)
        if args.update:
            db_m = m.sync(dbh.session)
            cout("INFO: marker: %s sync'd." % db_m.code)
        else:
            dbh.session.add(m)
            cout('INFO: marker %s added.' % m.code)


def do_initbatch(args, dbh):

    b = dbh.Batch()
    b.code = args.initbatch
    dbh.session.add(b)
    cout('INFO: batch %s added.' % b.code)



def do_initsample(args, dbh):

    if not args.batch:
        cerr('ERR: batch code must be supplied!')
        sys.exit(1)

    b = dbh.Batch.search(args.batch, dbh.session)
    cout('INFO - using batch code: %s' % b.code)

    inrows = csv.reader( open(args.initsample),
                delimiter = ',' if args.initsample.endswith('.csv') else '\t' )

    next(inrows)    # discard the 1st line

    counter = 0
    for row in inrows:
        s = b.add_sample( row[0] )
        counter += 1
        cout('INFO - sample: %s added.' % s.code)

    cout('INFO - number of new sample(s): %d' % counter)



def do_upload(args, dbh):

    cout('Uploading FSA files from input file: %s' % args.upload)

    b = dbh.get_batch(args.batch)

    inrows = csv.reader( open(args.upload),
                delimiter = ',' if args.upload.endswith('.csv') else '\t' )
    next(inrows)

    total_assay = 0
    line_counter = 1
    for row in inrows:

        line_counter += 1

        if not row[0] or row[0].startswith('#'):
            continue

        if len(row) < 3:
            cerr('ERR - line %d only has %d item(s)' % (line_counter, len(row)))

        sample_code, assay_filename, assay_panel = row[0], row[1], row[2]
        if len(row) >= 4:
            options = tokenize( row[3] )
        else:
            options = None

        try:

            s = b.search_sample(row[0])
            if not s:
                cerr('ERR - sample %s does not exist' % row[0])
                sys.exit(1)

            with open( args.fsadir + '/' + row[1], 'rb') as f:
                trace = f.read()

            a = s.add_assay( trace, filename=assay_filename, panel_code = assay_panel,
                        options = options, species = args.species )
            cerr('INFO - sample: %s assay: %s panel: %s has been uploaded' % 
                        (s.code, a.filename, assay_panel))

        except Exception as exc:

            if not args.test:
                raise
            cerr('ERR - line %d' % line_counter)
            cerr(' => %s' % str(exc))


def do_clearassay(args, dbh):

    cout('Clearing assay...')




