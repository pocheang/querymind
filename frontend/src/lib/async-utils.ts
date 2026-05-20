/**
 * Wraps an async function with loading state and error handling
 * For use in action creators (non-React contexts)
 */
export async function withAsyncHandler<T>(
  action: () => Promise<T>,
  options: {
    setLoading?: (loading: boolean) => void;
    onError?: (error: unknown, defaultMessage: string) => void | Promise<void>;
    errorMessage?: string;
  }
): Promise<T | undefined> {
  const { setLoading, onError, errorMessage = "操作失败" } = options;

  setLoading?.(true);
  try {
    const result = await action();
    return result;
  } catch (error) {
    await onError?.(error, errorMessage);
    return undefined;
  } finally {
    setLoading?.(false);
  }
}

/**
 * Creates a wrapped async function with automatic loading and error handling
 */
export function createAsyncAction<TArgs extends any[], TResult>(
  action: (...args: TArgs) => Promise<TResult>,
  options: {
    setLoading?: (loading: boolean) => void;
    onError?: (error: unknown, defaultMessage: string) => void | Promise<void>;
    errorMessage?: string;
  }
) {
  return async (...args: TArgs): Promise<TResult | undefined> => {
    return withAsyncHandler(() => action(...args), options);
  };
}
