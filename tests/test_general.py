import httplib


from ckan.config.middleware import make_app
from paste.deploy import appconfig
import paste.fixture
from ckan.tests import conf_dir, url_for, CreateTestData

from mockgoogleanalytics import runmockserver
from ckanext.googleanalytics.commands import LoadAnalytics
from ckanext.googleanalytics import dbutil


class MockClient(httplib.HTTPConnection):
    def request(self, http_request):
        filters = http_request.uri.query.get('filters')
        path = http_request.uri.path
        if filters:
            if "package" in filters:
                path += "/package"
            else:
                path += "/download"
        httplib.HTTPConnection.request(self,
                                       http_request.method,
                                       path)
        resp = self.getresponse()
        return resp


class TestConfig:
    def test_config(self):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        config.local_conf['ckan.plugins'] = 'googleanalytics'
        command = LoadAnalytics("loadanalytics")
        command.CONFIG = config.local_conf
        command.run([])

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()


class TestLoadCommand:
    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        config.local_conf['ckan.plugins'] = 'googleanalytics'
        config.local_conf['googleanalytics.username'] \
                              = 'borf'
        config.local_conf['googleanalytics.password'] \
                              = 'borf'
        config.local_conf['googleanalytics.profile_name'] \
                              = 'borf'
        config.local_conf['googleanalytics.show_downloads'] \
                              = 'true'
        cls.config = config.local_conf
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        env = {'HTTP_ACCEPT': ('text/html;q=0.9,text/plain;'
                               'q=0.8,image/png,*/*;q=0.5')}
        cls.app = paste.fixture.TestApp(wsgiapp, extra_environ=env)
        CreateTestData.create()
        runmockserver()

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()
        conn = httplib.HTTPConnection("localhost:%d" % 6969)
        conn.request("QUIT", "/")
        conn.getresponse()

    def test_top_packages(self):
        command = LoadAnalytics("loadanalytics")
        command.TEST_HOST = MockClient('localhost', 6969)
        command.CONFIG = self.config
        command.run([])
        packages = dbutil.get_top_packages()
        resources = dbutil.get_top_resources()
        assert packages[0][1] == 2
        assert resources[0][1] == 4

    def test_download_count_inserted(self):
        command = LoadAnalytics("loadanalytics")
        command.TEST_HOST = MockClient('localhost', 6969)
        command.CONFIG = self.config
        command.run([])
        response = self.app.get(url_for(controller='package',
                                        action='read',
                                        id='annakarenina'))
        assert "(4 downloads)" in response.body, response.body
