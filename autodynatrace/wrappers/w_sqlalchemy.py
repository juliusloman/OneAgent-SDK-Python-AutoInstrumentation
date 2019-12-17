import oneagent

from ..log import logger
from ..sdk import sdk

try:
    import sqlalchemy
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from sqlalchemy.engine.base import Connection

    logger.debug("Instrumenting sqlalchemy")

    @event.listens_for(Engine, "before_cursor_execute", named=True)
    def dynatrace_before_cursor_execute(**kw):
        logger.debug("Injected method before_cursor_execute")

        try:
            conn = kw["conn"]
            context = kw["context"]

            statement = kw.get("statement", "")
            db_technology = conn.engine.name
            db_name = conn.engine.url.database
            db_host = conn.engine.url.host
            db_port = conn.engine.url.port

            channel = oneagent.sdk.Channel(oneagent.sdk.ChannelType.OTHER)
            if db_host is not None and db_port is not None:
                channel = oneagent.sdk.Channel(oneagent.sdk.ChannelType.TCP_IP, "{}:{}".format(db_host, db_port))

            db_info = sdk.create_database_info(db_name, db_technology, channel)
            tracer = sdk.trace_sql_database_request(db_info, statement)
            tracer.start()
            context.dynatrace_tracer = tracer

        except Exception as e:
            logger.debug("Error instrumenting sqlalchemy: {}".format(e))

    @event.listens_for(Engine, "after_cursor_execute", named=True)
    def dynatrace_after_cursor_execute(**kw):
        logger.debug("Injected method after_cursor_execute")

        try:
            context = kw["context"]

            if context is not None and hasattr(context, "dynatrace_tracer"):
                tracer = context.dynatrace_tracer
                if tracer is not None:
                    # TODO Check if I get stats about query
                    tracer.end()

        except Exception as e:
            logger.debug("Error instrumenting sqlalchemy after_cursor_execute: {}".format(e))


except ImportError:
    pass