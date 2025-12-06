"""Retry utilities for handling transient failures."""

import time
from typing import Callable, TypeVar, Optional, List
from functools import wraps

from shared.logging_setup import get_logger
from shared.exceptions import ReplenishmentError

logger = get_logger(__name__)

T = TypeVar('T')


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_failure: Optional[Callable] = None
):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        on_failure: Optional callback function called on final failure
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.2f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        if on_failure:
                            on_failure(e)
                        raise
            
            # Should never reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry failure")
        
        return wrapper
    return decorator


def retry_database_operation(
    max_attempts: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0
):
    """
    Decorator specifically for database operations that may fail transiently.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        
    Returns:
        Decorated function
    """
    from sqlalchemy.exc import OperationalError, DisconnectionError
    
    return retry_on_failure(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=(OperationalError, DisconnectionError, ConnectionError)
    )


def safe_execute(
    func: Callable[..., T],
    default: Optional[T] = None,
    exceptions: tuple = (Exception,),
    log_error: bool = True
) -> Optional[T]:
    """
    Safely execute a function, returning a default value on failure.
    
    Args:
        func: Function to execute
        default: Default value to return on failure
        exceptions: Exceptions to catch
        log_error: Whether to log errors
        
    Returns:
        Function result or default value
    """
    try:
        return func()
    except exceptions as e:
        if log_error:
            logger.error(f"Error executing {func.__name__}: {e}")
        return default

