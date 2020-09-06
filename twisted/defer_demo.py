
import time
from twisted.internet import reactor, defer, task
from twisted.internet.defer import returnValue
from twisted.python import failure


class CallbackChain(object):
    '''
    callback chain of deferred:
    defer_list_example -- show the use of defer list
    handle_error_example -- show how to handle error
    semaphore_example -- show the use fo semaphore
    '''

    @classmethod
    def dummy_query(cls, input):

        def callback(input):
            print('Callback: dummy_query')
            if isinstance(input, str):
                return f'Success: Get result from {input}'
            elif isinstance(input, int):
                if input < 0:
                    return failure.Failure('Input error', ValueError)
                else:
                    return f'Success: result is {input}'
            else:
                return failure.Failure('Input error', TypeError)

        d = defer.Deferred()
        d.addCallback(callback)
        reactor.callLater(1, d.callback, input)
        return d

    @classmethod
    def print_query(cls, result):
        print('Callback: print_query')
        print(f'Result recv: {result}')

    @classmethod
    def list_query(cls, results):
        print('Callback: print_query')
        for success, result in results:
            if success:
                print(result)
            else:
                assert isinstance(result, failure.Failure)
                err = result.trap(TypeError, ValueError)
                if err == TypeError:
                    print('Error: you must input string or integer')
                elif err == ValueError:
                    print('Error: integer must lager than 0')

    @classmethod
    def err_callback(cls, failure):
        print(f'Catch Exception: {failure.getTraceback()}')
        err = failure.trap(TypeError, ValueError)
        if err == TypeError:
            print('you must input string or integer')
        elif err == ValueError:
            print('integer must lager than 0')

    @classmethod
    def defer_list_example(cls):
        print('Begin run')
        d1 = cls.dummy_query('www.google.com')
        d2 = cls.dummy_query(100)
        d3 = cls.dummy_query(-100)
        d4 = cls.dummy_query(b'I am byte')
        dl = defer.DeferredList([d1, d2, d3, d4], consumeErrors=True)
        dl.addCallback(cls.list_query)
        reactor.callLater(3, reactor.stop)
        reactor.run()

    @classmethod
    def handle_error_example(cls):
        d = cls.dummy_query(-100)
        d.addCallbacks(cls.print_query, cls.err_callback)
        reactor.callLater(3, reactor.stop)
        reactor.run()

    @classmethod
    def semaphore_example(cls):
        '''
        Run each function in sequence and return a Deferred
        that fires when all functions are completed.
        task.Cooperator more useful
        :return:
        '''
        inputs = [
            'www.google.com',
            'www.facebook.com',
            100,
            -100
        ]

        def _task(input):
            d: defer.Deferred = cls.dummy_query(input)
            d.addCallbacks(cls.print_query, cls.err_callback)

        sem = defer.DeferredSemaphore(10)
        deferreds = [sem.run(_task, input) for input in inputs]
        defer.gatherResults(deferreds)
        reactor.callLater(3, reactor.stop)
        reactor.run()

    @classmethod
    def task_cooperate_example(cls):

        inputs = [
            'www.google.com',
            'www.facebook.com',
        ]

        def _task():
            for input in inputs:
                d: defer.Deferred = cls.dummy_query(input)
                d.addCallbacks(cls.print_query, cls.err_callback)
                yield d

        coop = task.Cooperator()
        deferreds = [coop.coiterate(_task()) for _ in range(4)]
        defer.gatherResults(deferreds)
        reactor.callLater(3, reactor.stop)
        reactor.run()


class MultiTask(object):
    '''
    twisted internet task
    coiterate_example -- show task cooperate
    loop_call_example -- show the loop call
    '''

    @classmethod
    def dummy_compute(cls, input):

        def callback(input):
            print(f'Dummy compute Begin({input}): {time.time()}')
            total, limit = 0, 2 << 32
            for i in range(0, input):
                for j in range(0, i):
                    total += j
                    if total > limit:
                        total = 0
            print(f'Dummy compute end: {time.time()}')

        d = defer.Deferred()
        d.addCallback(callback)
        reactor.callWhenRunning(d.callback, input)
        return d

    @classmethod
    def coiterate_example(cls):
        coop = task.Cooperator()
        tasks = [cls.dummy_compute(input) for input in (1000, 2000, 3000)]
        d = coop.coiterate(iter(tasks))
        d.addBoth(lambda _: reactor.stop())
        reactor.run()

    @classmethod
    def loop_call_example(cls):
        MultiTask.loop_limit = 3
        MultiTask.current_loop = 0

        @defer.inlineCallbacks
        def dummy_query():

            def query():
                return f'query:{time.time()}'

            def callback(current_loop, result):
                print(f'current_loop:{current_loop},'
                      f'result:{result}')

            if MultiTask.current_loop < MultiTask.loop_limit:
                MultiTask.current_loop += 1
                result = yield task.deferLater(reactor, 1, query)
                returnValue(callback(MultiTask.current_loop, result))
            else:
                return loop.stop()

        def callback(result):
            print('Loop Done')
            reactor.stop()

        def err_callback(failure):
            print(failure.getBriefTraceback())
            reactor.stop()

        loop = task.LoopingCall(dummy_query)
        loop_deferred = loop.start(1)
        loop_deferred.addCallbacks(callback, err_callback)
        reactor.run()


if __name__ == '__main__':
    # CallbackChain.defer_list_example()
    # CallbackChain.handle_error_example()
    # CallbackChain.semaphore_example()
    # CallbackChain.task_cooperate_example()
    MultiTask.loop_call_example()
