import os
basedir = os.path.abspath(os.path.dirname(__file__))

DEFAULT_PROD_DB_URI = os.path.join(basedir, 'database/app.db')
SQLITE_DEFAULT_PROD_DB_URI = 'sqlite:///{}'.format(DEFAULT_PROD_DB_URI)


class Config(object):
    TESTING = False
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URI')
                               or SQLITE_DEFAULT_PROD_DB_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATA_DIRECTORY = os.environ.get('DATA_DIRECTORY')
    PIPELINE_DIRECTORY = os.environ.get('PIPELINE_DIRECTORY')
    DATA_REMOTE_SIBLING = os.environ.get('DATA_REMOTE_SIBLING')


class ProductionConfig(Config):
    pass


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'test/database/app.db')
