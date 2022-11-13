from __future__ import with_statement
from cuisine import *
from fabric.api import *

GIT_MASTER_REPO = 'git@github.com:suitemedia/suite.git'

env.user = "suite"
env.compress = False
env.collectstatic = False
env.migrate = True
env.staging = False
env.compile_templates = True
env.staging_aws_url = '//d3352dq5876lbj.cloudfront.net/'
env.prod_aws_url = '//static.suite.io/'
env.aws_url = env.staging_aws_url
env.hosts = ['52.3.250.222'] # this is app1

def prod():
    env.aws_url = env.prod_aws_url
    env.s3BaseUrl = 's3ProdBaseUrl'

def prod_app1():
    prod()
    env.collectstatic = True
    env.hosts = ['52.3.250.222']

def prod_node1():
    prod()
    env.migrate = False
    env.user = 'suite'
    env.hosts = ['54.85.79.112']

def prod_tasks():
    prod()
    env.migrate = False
    env.hosts = ['54.85.217.176']

def recreate_sym_link(from_path, to_path, sudo=True):
    """ remove old symbolic link if necessary and create new one """
    if sudo:
        if dir_exists(to_path) or file_exists(to_path):
            run('sudo rm -f %s' % to_path)
        run('sudo ln -sf %s %s' % (from_path, to_path))
    else:
        if dir_exists(to_path) or file_exists(to_path):
            run('rm -f %s' % to_path)
        run('ln -sf %s %s' % (from_path, to_path))

def pull_changeset(changeset_id, username='suite'):
    run('cd /home/%s/code/suite/reference; \
        git clone %s /home/%s/code/suite/changesets/%s; \
        cd /home/%s/code/suite/changesets/%s; \
        git reset --hard %s' % (username, GIT_MASTER_REPO, username, changeset_id, username, changeset_id, changeset_id))


def production_less_inject_s3_url():
    def update_s3_url(text):
        res = []
        print('hi, nice to see you')
        try:
            test = text.split("\n")
        except Exception as e:
            print('ooh, problem here: %s' % e)
        for line in text.split("\n"):
            if "assetBaseUrl" in line:
                print('check1')
                try:
                    new_line = line.replace("localStaticUrl", env.s3BaseUrl)
                except Exception as e:
                    print('failed to parse line: %s' % e)
                res.append(new_line)
            else:
                res.append(line)
        return "\n".join(res)

    def update_less(text):
        res = []
        for line in text.split("\n"):
            res.append(line)
        return "\n".join(res)

    file_update('/home/suite/code/suite/live/static/less/suite/variables.less', update_s3_url)

def migrate():
    run('cd /home/suite/code/suite/live/; echo "yes" | python manage.py migrate')

def collect_static():
    run('cd /home/suite/code/suite/live; echo "yes" | python manage.py collectstatic; python manage.py compress --force')

def _pull(changeset_id=None, branch=None, username='suite'):
    # make sure we have a reference/master copy of the code on this server
    if not dir_exists('/home/%s/code/suite/reference' % username):
        run('git clone %s /home/%s/code/suite/reference' % (GIT_MASTER_REPO, username))

    # update to the latest
    run('cd /home/%s/code/suite/reference; git pull' % username)

    # if we specify a changeset, grab that
    if changeset_id:
        if not dir_exists('/home/%s/code/suite/changesets/%s' % changeset_id):
            pull_changeset(changeset_id, username)
    else:
        if branch:
            run('cd /home/%s/code/suite/reference; git checkout %s' % (username, branch))
        else:
            run('cd /home/%s/code/suite/reference; git checkout master' % username)

        run('cd /home/%s/code/suite/reference; git pull' % username)

        result = run('cd /home/%s/code/suite/reference; git rev-parse HEAD' % username)
        changeset_id = result.split(' ')[0]
        if not dir_exists('/home/%s/code/suite/changesets/%s' % (username, changeset_id)):
            pull_changeset(changeset_id, username)

    # change the symbolic link if it exists
    recreate_sym_link('/home/%s/code/suite/changesets/%s' % (username, changeset_id), '/home/%s/code/suite/live' % username, False)

def deploy_node(changeset_id=None, branch=None):
    # grab the code
    _pull(changeset_id, branch, 'suite')
    recreate_sym_link('/home/suite/node_build/node_modules', '/home/suite/code/suite/live/node_modules', False)
    recreate_sym_link('/home/suite/node_build/node/node_modules', '/home/suite/code/suite/live/node/node_modules', False)
    run('cd /home/suite/code/suite/live; grunt precompileHandlebarsServer; npm install')
    run('cd /home/suite/code/suite/live/node; npm install')

    if env.staging:
        run('cp /home/suite/code/suite/live/node/newrelic.staging.js /home/suite/code/suite/live/node/newrelic.js')

    with settings(warn_only=True):
        run('cd /home/suite/code/suite/live; forever stopall')
    run('cd /home/suite/code/suite/live/node; NODE_ENV=production forever start -a -l /home/suite/logs/forever.log -o /home/suite/logs/out.log -e /home/suite/logs/err.log app.js')

    with settings(warn_only=True):
        run("cd /home/suite/code/suite/changesets/; ls -t | sed -e '1,20d' | sudo xargs -d '\n' rm -rf")

def deploy(changeset_id=None, branch=None):
    # grab the code
    _pull(changeset_id, branch)

    recreate_sym_link('/home/suite/.env', '/home/suite/code/suite/live/.env', False)

    # make sure we have all our requirements installed
    run('cd /home/suite/code/suite/live/; pip install -r requirements.txt')
    # run('cd /home/suite/code/suite/live/; pip install requests-oauthlib --upgrade --force')

    if env.collectstatic:
        # print('------ about to inject s3 urls into less')
        # try:
        #     print('- here we go')
        #     production_less_inject_s3_url()
        #     print('- from the other side?')
        # except Exception as e:
        #     print('failed to inject s3 urls: %s' % e)
        # print('did that')
        recreate_sym_link('/home/suite/node_build/node_modules', '/home/suite/code/suite/live/node_modules', False)
        run('cd /home/suite/code/suite/live; npm install')
        run('cd /home/suite/code/suite/live; grunt makeLess')
        run('cd /home/suite/code/suite/live; grunt precompileHandlebars') 
        collect_static()

    # compile django templates
    # if env.compile_templates:
    #     run('cd /home/suite/code/suite/live/; python manage.py compile_templates -v 2 --all --noinput --boring')

    if env.migrate:
        migrate()

    if env.staging:
        run('cp /home/suite/code/suite/live/django.staging.ini /home/suite/code/suite/live/django.ini')
        run('cp /home/suite/code/suite/live/newrelic.staging.ini /home/suite/code/suite/live/newrelic.ini')
        run('cp /home/suite/code/suite/live/robots.staging.txt /home/suite/code/suite/live/robots.txt')

    run('restart-suite.sh')

    # oh, and just to keep our drive clean, let's make sure we only keep at most 20 changesets alive in this directory
    # run it with warn_only because the xargs will fail if we don't have enough to actually delete
    with settings(warn_only=True):
        run("cd /home/suite/code/suite/changesets/; sudo ls -t | sudo sed -e '1,20d' | sudo xargs -d '\n' rm -rf")

def toggle_login(disable_login):
    def update_env(text):
        res = []
        for line in text.split("\n"):
            if "LOGIN_DISABLED" in line:
                new_line = "LOGIN_DISABLED=%s" % disable_login
                res.append(new_line)
            else:
                res.append(line)
        return "\n".join(res)

    file_update('/home/suite/.env', update_env)
    run('restart-suite.sh')


def deploy_nginx():
    run('cd /home/suite/code/suite/live/; git pull;')
    run('sudo cp /home/suite/code/suite/live/ops/nginx/app_server_nginx.conf /etc/nginx/sites-available/suite')
    run('sudo /etc/init.d/nginx restart')

def disable_login():
    toggle_login(True)

def enable_login():
    toggle_login(False)

def prod_flush_caches():
    run('cd /home/suite/code/suite/live/; python manage.py flush_elasticache us-east-1 suite-gen-memcached')
