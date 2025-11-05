"""
Error recovery and circuit breaker for trading bot
"""
import asyncio
from typing import Optional, Dict, Callable, Any
from datetime import datetime, timedelta
from enum import Enum

from app.utils.logger import log


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Too many failures, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                log.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            log.info("Circuit breaker recovered, returning to CLOSED state")
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            log.error(
                f"Circuit breaker tripped! {self.failure_count} failures. "
                f"Entering OPEN state for {self.recovery_timeout}s"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to recover"""
        if not self.last_failure_time:
            return False
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def reset(self):
        """Manually reset the circuit breaker"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        log.info("Circuit breaker manually reset")


class RetryPolicy:
    """
    Retry policy with exponential backoff
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    log.info(f"Retry successful on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = min(
                        self.initial_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    
                    log.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    log.error(f"All {self.max_attempts} attempts failed: {e}")
        
        raise last_exception


class ErrorTracker:
    """
    Track errors and their frequency
    """
    
    def __init__(self, window_size: int = 3600):
        """
        Args:
            window_size: Time window in seconds for tracking errors
        """
        self.window_size = window_size
        self.errors: Dict[str, list] = {}
    
    def record_error(self, error_type: str, details: str = ""):
        """Record an error occurrence"""
        now = datetime.utcnow()
        
        if error_type not in self.errors:
            self.errors[error_type] = []
        
        self.errors[error_type].append({
            "timestamp": now,
            "details": details
        })
        
        # Clean old errors outside window
        self._clean_old_errors(error_type, now)
    
    def get_error_count(self, error_type: str) -> int:
        """Get count of errors within the time window"""
        if error_type not in self.errors:
            return 0
        
        now = datetime.utcnow()
        self._clean_old_errors(error_type, now)
        
        return len(self.errors[error_type])
    
    def get_error_rate(self, error_type: str) -> float:
        """Get error rate per minute"""
        count = self.get_error_count(error_type)
        return count / (self.window_size / 60)
    
    def get_all_errors(self) -> Dict[str, int]:
        """Get counts for all error types"""
        return {
            error_type: self.get_error_count(error_type)
            for error_type in self.errors.keys()
        }
    
    def _clean_old_errors(self, error_type: str, now: datetime):
        """Remove errors outside the time window"""
        if error_type not in self.errors:
            return
        
        cutoff = now - timedelta(seconds=self.window_size)
        self.errors[error_type] = [
            err for err in self.errors[error_type]
            if err["timestamp"] > cutoff
        ]
    
    def clear(self):
        """Clear all error history"""
        self.errors.clear()


class RateLimiter:
    """
    Rate limiter to prevent API throttling
    """
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        now = datetime.utcnow()
        
        # Remove old calls outside window
        cutoff = now - timedelta(seconds=self.time_window)
        self.calls = [call for call in self.calls if call > cutoff]
        
        # Check if we need to wait
        if len(self.calls) >= self.max_calls:
            # Calculate wait time
            oldest_call = min(self.calls)
            wait_until = oldest_call + timedelta(seconds=self.time_window)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                log.debug(f"Rate limit reached, waiting {wait_seconds:.2f}s")
                await asyncio.sleep(wait_seconds)
                
                # Retry acquire after waiting
                return await self.acquire()
        
        # Record this call
        self.calls.append(now)
    
    def reset(self):
        """Reset the rate limiter"""
        self.calls.clear()

