import { useState } from "react";

export function useFormState() {
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const reset = () => {
    setStatus("");
    setError("");
    setLoading(false);
  };

  return {
    status,
    setStatus,
    error,
    setError,
    loading,
    setLoading,
    reset
  };
}
