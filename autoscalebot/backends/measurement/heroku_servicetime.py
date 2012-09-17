import re
import urllib2
from autoscalebot.backends.measurement.base import BaseMeasurementBackend
from autoscalebot.logger import logger


class HerokuServiceTimeBackend(BaseMeasurementBackend):
    """
    This backend measures the internal service time of the last test request on heroku

    It accepts the following parameters:

    HEROKU_APP, which is a heroku app object from the heroku library (optional:
                it will use the app derived from the scaling backend if left out),
    MEASUREMENT_URL, which defaults to "/autoscalebot/measurement/", and
    MAX_RESPONSE_TIME_IN_SECONDS, which defaults to 30.

    Its measure method returns a dictionary, with the following format:

    {
        'backend': 'HerokuServiceTimeBackend',
        'data': 350, // ms
        'success': True,  // assuming it was
    }
    """
    def __init__(self, *args, **kwargs):
        super(HerokuServiceTimeBackend, self).__init__(*args, **kwargs)

        if self.settings.HEROKU_APP:
            self.heroku_app = self.settings.HEROKU_APP
        else:
            self.heroku_app = self.settings.scaling_backend.heroku_app
        self.url = self.settings.MEASUREMENT_URL
        self.cleaned_url = self.url.replace("http://", "").replace("https://", "")
        if self.cleaned_url[-1] == "/":
            self.cleaned_url = self.cleaned_url[:-1]

    def default_settings(self):
        base_defaults = super(self, "default_settings")()
        base_defaults.update({
            "heroku_app": "my-app",
            "timeout_in_seconds": 30,
        })
        return base_defaults

    def measure(self, *args, **kwargs):
        success = True
        service_time = 0

        try:
            response = urllib2.urlopen(self.url, None, self.settings.MAX_RESPONSE_TIME_IN_SECONDS)
            assert response.read(1) is not None
        except:  # probably URLError, but anything counts.
            logger.debug("Error getting response from %s." % self.url)
            success = False

        if success:
            line = False
            service_pattern = r'service=([\d]*)ms'
            try:
                for line in self.heroku_app.logs(num=1, tail=True):
                    if self.cleaned_url in line and "service=" in line:
                        matches = re.findall(service_pattern, line)
                        service_time = int(matches[0])
                        success = True
            except:
                pass

        if not success:
            logger.debug("Measurement call not found in logs.")

        return {
            'backend': 'HerokuServiceTimeBackend',
            'data': service_time,
            'success': success
        }