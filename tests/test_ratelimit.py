from codelens.security.ratelimit import SlidingWindowLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0


    def __call__(self):
        return self.now

    
def test_allows_up_to_the_limit_then_refuses():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(3, 10, clock)
    assert [limiter.allow("a") for _ in range(5)] == [True, True, True, False, False]


def test_window_slides():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, 10, clock)
    assert limiter.allow("a")    
    clock.now = 5
    assert limiter.allow("a")      
    assert not limiter.allow("a")     
    clock.now = 10                     
    assert limiter.allow("a")
    assert not limiter.allow("a")


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(1, 10, FakeClock())
    assert limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("a")


def test_refused_requests_do_not_extend_the_block():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, 10, clock)
    limiter.allow("a")             
    clock.now = 9
    assert not limiter.allow("a") 
    clock.now = 10
    assert limiter.allow("a")

    
def test_retry_after():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, 10, clock)
    assert limiter.retry_after("a") == 0.0
    limiter.allow("a")
    clock.now = 4
    assert limiter.retry_after("a") == 6.0