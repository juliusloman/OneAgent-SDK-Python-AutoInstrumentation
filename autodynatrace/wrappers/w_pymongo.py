import oneagent

from ..log import logger
from ..sdk import sdk

try:
    from pymongo import monitoring

    class DynatraceMongoListener(monitoring.CommandListener):
        def __init__(self):
            self.vendor = "MongoDB"
            self._tracer_dict = {}

        def started(self, event):

            try:
                db_name = event.database_name
                collection_name = event.command.get(event.command_name)
                operation = event.command_name
                host, port = event.connection_id
                channel = oneagent.sdk.Channel(oneagent.sdk.ChannelType.TCP_IP, "{}:{}".format(host, port))

                db_info = sdk.create_database_info("{}.{}".format(db_name, collection_name), self.vendor, channel)
                tracer = sdk.trace_sql_database_request(db_info, operation)
                self._tracer_dict[_get_tracer_dict_key(event)] = tracer
                tracer.start()

            except Exception as e:
                logger.debug("Error instrumenting MongoDB: {}".format(e))

        def succeeded(self, event):
            self.end(False, event)

        def failed(self, event):
            self.end(True, event, message="{}".format(event.failure))

        def end(self, failed, event, message=""):
            tracer = self._tracer_dict.get(_get_tracer_dict_key(event))
            if tracer is not None:
                if event:
                    tracer.mark_failed("MongoDB Command", message)

                tracer.end()
                self._tracer_dict.pop(_get_tracer_dict_key(event))

    monitoring.register(DynatraceMongoListener())

    def _get_tracer_dict_key(event):
        if event.connection_id is not None:
            return event.request_id, event.connection_id
        return event.request_id

    logger.debug("Instrumenting pymongo")
except ImportError:
    pass
