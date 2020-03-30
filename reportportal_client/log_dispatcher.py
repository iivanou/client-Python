import logging
import threading

from six.moves import queue

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class QueueListener(object):
    _sentinel_item = None

    def __init__(self, queue, *handlers, **kwargs):
        self.queue = queue
        self.queue_get_timeout = kwargs.get("queue_get_timeout", None)
        self.handlers = handlers
        self._stop_nowait = threading.Event()
        self._stop = threading.Event()
        self._thread = None

    def dequeue(self, block=True):
        """Dequeue a record and return item."""
        return self.queue.get(block, self.queue_get_timeout)

    def start(self):
        """Start the listener.

        This starts up a background thread to monitor the queue for
        items to process.
        """
        self._thread = t = threading.Thread(target=self._monitor)
        t.setDaemon(True)
        t.start()

    def prepare(self, record):
        """Prepare a record for handling.

        This method just returns the passed-in record. You may want to
        override this method if you need to do any custom marshalling or
        manipulation of the record before passing it to the handlers.
        """
        return record

    def handle(self, record):
        """Handle an item.

        This just loops through the handlers offering them the record
        to handle.
        """
        record = self.prepare(record)
        for handler in self.handlers:
            handler(record)

    def _monitor(self):
        """Monitor the queue for items, and ask the handler to deal with them.

        This method runs on a separate, internal thread.
        The thread will terminate if it sees a sentinel object in the queue.
        """
        err_msg = ("invalid internal state:"
                   " _stop_nowait can not be set if _stop is not set")
        assert self._stop.isSet() or not self._stop_nowait.isSet(), err_msg

        q = self.queue
        has_task_done = hasattr(q, 'task_done')
        while not self._stop.isSet():
            try:
                record = self.dequeue(True)
                if record is self._sentinel_item:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                pass

        # There might still be records in the queue,
        # handle then unless _stop_nowait is set.
        while not self._stop_nowait.isSet():
            try:
                record = self.dequeue(False)
                if record is self._sentinel_item:
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                break

    def stop(self, nowait=False):
        """Stop the listener.

        This asks the thread to terminate, and then waits for it to do so.
        Note that if you don't call this before your application exits, there
        may be some records still left on the queue, which won't be processed.
        If nowait is False then thread will handle remaining items in queue and
        stop.
        If nowait is True then thread will be stopped even if the queue still
        contains items.
        """
        self._stop.set()
        if nowait:
            self._stop_nowait.set()
        self.queue.put_nowait(self._sentinel_item)
        if (self._thread.isAlive() and
                self._thread is not threading.currentThread()):
            self._thread.join()
        self._thread = None


class LogDispatcher(object):
    def __init__(self, rp_disp, queue, log_batch_size=20, queue_get_timeout=5,
                 error_handler=None):
        self.listener = None
        self.lock = None

        self.rp_disp = rp_disp
        self.error_handler = error_handler
        self.log_batch_size = log_batch_size
        self.queue_get_timeout = queue_get_timeout
        self.log_batch = []
        self.queue = queue

    def start(self):
        self.listener = QueueListener(self.queue, self.process_log,
                                      queue_get_timeout=queue_get_timeout)
        self.listener.start()
        self.lock = threading.Lock()

    def terminate(self, nowait=False):
        """Finalize and stop service

        Args:
            nowait: set to True to terminate immediately and skip processing
                messages still in the queue
        """
        logger.debug("Acquiring lock for service termination")
        with self.lock:
            logger.debug("Terminating service")

            if not self.listener:
                logger.warning("Service already stopped.")
                return

            self.listener.stop(nowait)

            try:
                if not nowait:
                    self._post_log_batch()
            except Exception:
                if self.error_handler:
                    self.error_handler(sys.exc_info())
                else:
                    raise
            finally:
                self.queue = None
                self.listener = None

    def _post_log_batch(self):
        logger.debug("Posting log batch size: %s", len(self.log_batch))
        if self.log_batch:
            try:
                self.rp_disp.save_log_batch(self.log_batch)
            finally:
                self.log_batch = []

    def process_log(self, **log_item):
        """Special handler for log messages.

        Accumulate incoming log messages and post them in batch.
        """
        logger.debug("Processing log item: %s", log_item)
        self.log_batch.append(log_item)
        if len(self.log_batch) >= self.log_batch_size:
            self._post_log_batch()
