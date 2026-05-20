export function validateUsername(value: string): boolean {
  return /^[A-Za-z0-9._-]{3,32}$/.test(value.trim());
}

export function validatePassword(value: string): boolean {
  return (
    value.length >= 12 &&
    /[a-z]/.test(value) &&
    /[A-Z]/.test(value) &&
    /[0-9]/.test(value) &&
    /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value)
  );
}

export function getPasswordRequirements(password: string) {
  return {
    length: password.length >= 12,
    lowercase: /[a-z]/.test(password),
    uppercase: /[A-Z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(password)
  };
}
