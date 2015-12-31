""" logging from multiple processes to a single handler is critical to wasatch
application goals. These tests ensure that the various components of the
application all log to same location on disk.

As of 2015-12-30 10:39, it is unknown how to work with py.test and the
capturelog fixture to read the log prints to stdout/stderr streams. The
workaround is to store all of the log events to disk, and re-read the file at
test completion.

"""

import os
import time
import logging
import multiprocessing

from pysideapp import app_logging

FILENAME = "mptest_log.txt"

class TestLogFile():
    def test_log_file_is_created(self):
        assert self.delete_log_file_if_exists() == True

        main_logger = app_logging.MainLogger()
        main_logger.close()

        time.sleep(0.5) # required to let file creation happen

        assert self.log_file_created() == True


    def test_log_file_has_entries(self):
        assert self.delete_log_file_if_exists() == True

        main_logger = app_logging.MainLogger()
        main_logger.close()

        time.sleep(0.5) # required to let file creation happen

        log_text = self.get_text_from_log()

        assert "Top level log configuration" in log_text


    def test_log_capture_fixture_can_read_top_level_log(self, caplog):
        main_logger = app_logging.MainLogger()
        main_logger.close()

        assert "Top level log configuration" in caplog.text()


    def test_log_capture_fixture_does_not_see_sub_process_entries(self, caplog):
        """ This test is about documenting the expected behavior. It took days
        of effort to determine that the logging is behaving as expected, but the
        pytest capture fixtures does not seem to be able to record those values.
        """
        main_logger = app_logging.MainLogger()

        log_queue = main_logger.log_queue
        sub_proc = multiprocessing.Process(target=self.worker_process,
                                           args=(log_queue,))
        sub_proc.start()

        time.sleep(1.0) # make sure the process has enough time to emit

        main_logger.close()

        time.sleep(0.5) # required to let file creation happen

        log_text = caplog.text()

        assert "Top level log configuration" in log_text
        assert "Sub process setup configuration" not in log_text
        assert "Sub process debug log info" not in log_text

    def test_log_file_has_sub_process_entries(self):
        """ This test documents the alternative: slurp the log results back in
        from the log file and then do the text matches.
        """
        assert self.delete_log_file_if_exists() == True

        main_logger = app_logging.MainLogger()

        log_queue = main_logger.log_queue
        sub_proc = multiprocessing.Process(target=self.worker_process,
                                           args=(log_queue,))
        sub_proc.start()

        time.sleep(1.0) # make sure the process has enough time to emit

        main_logger.close()

        time.sleep(0.5) # required to let file creation happen

        log_text = self.get_text_from_log()

        assert "Top level log configuration" in log_text
        assert "Sub process setup configuration" in log_text
        assert "Sub process debug log info" in log_text


    def worker_process(self, log_queue):
        """ Simple multi-processing target that uses the helper log
        configuration in app_logging, and logs the current process name and an
        expected string.
        """

        app_logging.process_log_configure(log_queue)

        # The root logger has now been created for this process, along with the
        # queue handler. Get a reference to the root_log and write a debug log
        # entry. In a real application the module level log =
        # logging.getLogger(__name__) still will be called, but then the log
        # module level variable will be overwritten witht the root logger
        # created in the app_logging.process_log_configure call above.
        root_log = logging.getLogger()

        name = multiprocessing.current_process().name
        #print('Worker started: %s' % name)
        root_log.debug("%s Sub process debug log info", name)
        #print('Worker finished: %s' % name)



    def get_text_from_log(self):
        """ Mimic the capturelog style of just slurping the entire log
        file contents.
        """

        log_text = ""
        log_file = open(FILENAME)
        for line_read in log_file:
            log_text += line_read
        return log_text


    def log_file_created(self):
        """ Helper function that returns True if file exists, false otherwise.
        """
        filename = FILENAME
        if os.path.exists(filename):
            return True

        return False

    def delete_log_file_if_exists(self):
        """ Remove the specified log file and return True if succesful.
        """
        filename = FILENAME

        if os.path.exists(filename):
            os.remove(filename)

        if os.path.exists(filename):
            print "Problem deleting: %s", filename
            return False
        return True
